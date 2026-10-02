# V2 baseline comparison: methods and boundaries

`compare_datasets(baseline_df, current_df, policy=DriftPolicy(...))` returns JSON-compatible comparison schema **2.0**: `summary`, `schema`, `dataset_metrics`, shared `columns`, ordered `findings`, and the complete effective `policy`. Results have no timestamp or filename; runtime metadata belongs to optional history. App version is 2.0.0. V1 profile schema 1.4 and score policy 1.0 are unchanged.

## Direction and denominators

Signed changes are **current minus baseline**. Relative change is `100 * difference / abs(baseline)` when the baseline is nonzero. Absolute differences of rates are **percentage points**, separately from relative percentage change. Zero baseline or absent denominator yields JSON `null`/UI N/A. Zero rows or no shared columns yields `not_comparable`.

Missingness uses pandas nulls. Duplicates count exact repeated rows after the first, divided by rows. Overall missingness divides missing cells by all cells; schema changes affect this denominator. Uniqueness divides distinct non-null values by non-null observations. These follow pandas semantics, not declared key constraints.

## Schema and representation

Added columns are informational; removed columns are moderate review findings. Dtype changes with the same inferred family (such as int to float) are informational. Nonempty family changes are moderate. Numeric-like text and datetime-like text use an 80% parseability threshold. These are observed representations, not intended semantics; empty columns have unknown semantics.

Datetime strings require explicit year-first `YYYY-MM-DD` syntax, optionally followed by time, and successful parsing. Ambiguous regional dates and bare epoch numbers are not guessed. Native timestamps become UTC. Date-only, timestamp-text and native representation changes are informational, even when coverage is identical. Malformed non-null dates affect parseability, not missingness.

## Numeric distributions

**KS distance** is `max_x |F_baseline(x) - F_current(x)|` over combined observed support, in [0, 1]. Sorted Python numeric values and a two-pointer scan preserve integer ordering above 2^53 and handle ties together. No bins, smoothing, SciPy dependency, p-values, random sampling or significance claims are involved. The distance matches the two-sided statistic in the [SciPy primary documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html); this application does not implement the hypothesis test.

Statistics include finite count, mean, median, sample standard deviation (`ddof=1`), min/max and 5/25/75/95 percentiles. Nulls/infinities are excluded from the distribution; positive/negative infinity counts remain visible. Fewer than two finite values gives undefined std; an empty finite sample gives undefined distance. Constant shifts can have distance one.

Moments and quantiles use a scaled, canonically sorted float64 workspace to avoid square overflow and row-order-dependent summation. Extrema and KS retain parsed integer ordering; moments/quantiles remain approximate for large integers. V1's finite magnitude limit **1e150** also applies to V2, including numbers in object columns. Larger values are safely rejected. Numeric-looking CSV strings are not silently coerced into native numeric comparisons.

## Categorical distributions and cardinality

**Total variation distance (TVD)** is `0.5 * sum(|p_baseline(category) - p_current(category)|)` over the union of categories, excluding nulls. It lies in [0, 1]; zero means identical observed proportions. Unseen categories have zero probability on the other side, so no smoothing is needed. Membership changes are informational. Mixed object category keys distinguish strings, numbers and booleans.

All values contribute to exact counters. Up to ten category changes/new/disappeared examples are displayed, truncated to 80 characters each; truncated labels need not be unique. Full support, not displayed top categories, determines TVD. If union cardinality exceeds 200, or either side has at least 20 non-null values and uniqueness >= V1's 0.95 advisory cutoff, composition details and TVD are suppressed. New/disappeared counts and cardinality remain visible without category labels. Some legitimate diverse fields are suppressed; no identifier role is established.

Unique-count changes >=50% are informational. Uniqueness-ratio changes have separate bands. Sample-size changes can naturally change observed cardinality.

## Datetime coverage

Coverage includes earliest/latest UTC timestamp, span in days, parsed count and unique timestamp count. With at least 20 distinct timestamps per side, a span at most half the baseline or a current end at least one day earlier produces a moderate finding. Later windows are observed, not automatically suspicious.

Internal gaps are reported only when every baseline distinct-timestamp interval is exactly equal and positive, and a current interval exceeds three times that cadence. Irregular baselines imply no schedule. This is comparison against observed coverage, not a business calendar, freshness SLA, seasonality model or cause.

## Centralized heuristic thresholds

Frozen, validated `drift.DriftPolicy` controls all thresholds and display limits; results embed its effective values.

| Signal | Moderate | High |
|---|---:|---:|
| Shared-column missingness | 5 pp | 20 pp |
| Overall missing/duplicate rates | 5 pp | 20 pp |
| Relative row-count change | 20% | 50% |
| KS distance | 0.10 | 0.25 |
| Categorical TVD | 0.10 | 0.25 |
| Uniqueness-ratio change | 10 pp | 30 pp |

These are simple review policies, **not significance cutoffs or calibrated probabilities**. Absolute magnitudes are used: improvements also count as change. KS/TVD and cardinality alerts require at least 20 appropriate observations per side. Small-sample metrics can be displayed but are explicitly unassessed for distribution severity. This minimum does not establish representativeness or statistical power. Dataset counts/rates and schema changes remain direct observations, even for small inputs.

Any high finding, or at least three moderate findings, gives **High observed drift**; otherwise any moderate gives **Moderate**; informational findings alone give **Low**. Related findings can overlap. This is not a score or probability. **Low drift does not mean healthy data**: identical bad datasets, all-null columns and skipped distributions can have low drift. The UI shows assessment coverage.

## Trust and privacy

Band comparisons use a centralized 1e-12 absolute/relative numerical tolerance to avoid missing exact decimal boundaries such as a theoretical TVD of 0.10 represented as 0.09999999999999998. This is floating arithmetic tolerance, not statistical uncertainty or a different severity policy.

Core comparison and authored guidance need no provider. `comparison_llm.py` sends allowlisted numeric evidence and anonymous finding IDs/kinds, never filenames, column names, category labels, raw examples, timestamps or extrema. Model output cannot replace facts, order or severity. V1 schema/identity/order and lexical validation are reused, with additional causal/significance/severity phrase rejection. Failed/rejected output retains authored guidance and report access. Generated text says "Generated interpretation. Verify before acting."

These guards do not semantically verify prose. Paraphrased falsehoods can pass; harmless negated wording can be rejected. No V2 live-provider success or measured explanation-quality benefit is claimed. Comparison Markdown exports omit generated prose and category values; names and aggregates remain sensitive.

## Local history

History is disabled unless the administrator sets **QA_HISTORY_PATH**. On trusted single-user installations the UI offers explicit Save and recent-run inspection. SQLite stores run ID, timestamp, sanitized basename filenames, row counts, status, finding-type counts and comparison version. It retains 50 runs using transactions/idempotent IDs. No datasets, column names, categories or AI text are stored. Filenames can still be sensitive.

Detected non-database/corrupt files are preserved with a `.corrupt-<id>` suffix before a new history is created. Bad JSON records are skipped with a warning. Locked/incompatible databases are not renamed/reset. Quarantined files are not automatically deleted. This is not authentication, tenant isolation or durable cloud storage. Leave history disabled on public demos; enabled history is shared across visitors to that installation.

## Performance and omissions

All rows are analyzed without sampling. Numeric sorting is O((n+m) log(n+m)); category counting is linear before support sorting. Per-input V1 guards remain 10 MiB, 200k rows, 200 columns, 2m cells and 256 MiB deep-frame memory. Two frames, uploads and intermediates coexist; these are not process/host budgets. The shared reentrant analysis lock still protects process-global warning contexts.

Derived baseline snapshots are deferred: exact empirical KS needs the empirical distribution, potentially approaching raw-value retention, and category snapshots add privacy/versioning semantics. Direct file comparison is complete. Also omitted: autonomous investigation, model-executed Python/SQL, automatic cleaning, causality, forecasting, external storage, authentication and SaaS infrastructure.
