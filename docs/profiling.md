# Profiling reference

## Definitions

- Duplicate count uses `DataFrame.duplicated()` (all occurrences after the first); percentage = `100 * duplicate_rows / rows`.
- Missing values use pandas CSV defaults (`NA`, `NaN`, empty fields, etc.). Whitespace-only strings are not automatically treated as missing.
- Unique ratio = distinct non-null values / non-null rows. Most-frequent percentage uses non-null rows. Frequency ties follow pandas value-count order.
- Constant = one unique non-null value. Near-constant = at least 95% of non-null rows equal the most frequent value, excluding constants. All-null columns are missingness issues, not constants.
- Possible ID = unique ratio >= 0.95, object/string or integer-like numeric type, and median non-null string length <= 80. Floating values count as integer-like only if every non-null value is finite and integral. IDs are advisory, with no inferred target or modeling role. Date strings may also be flagged.
- Numeric describe and IQR statistics apply to numeric dtypes, excluding booleans, using finite values. Q1 and Q3 use pandas default linear quantiles. Fences are Q1 - 1.5 * IQR and Q3 + 1.5 * IQR. Outliers lie strictly outside. Percentage denominator is finite observations in that column. Zero IQR still uses the same formula. Infinities are reported separately and omitted from describe/histograms.
- Date parseability = successful parses / non-null values. String candidates require an explicit four-digit year and must not be bare numbers, preventing IDs from being treated as epoch dates and incomplete dates from depending on the current date. Parsing uses pandas mixed formats, UTC, month-first defaults. Native datetime values count as parseable; numeric dtypes are not parsed as dates.
- Mixed type = an object/string column with some, but not all, values parseable as numbers or some, but not all, parseable as dates. Its triggering minority percentage is the larger of the numeric and date minority shares. This is deliberately a review heuristic, not an instruction to coerce values.
- Profile 1.2 exposes numeric/date/neither parsing counts and up to three distinct examples per group, truncated to 80 characters, locally only. Numeric strings use `numeric-like text`, or `identifier-like text` if leading-zero integers are observed. Native numeric values remain numeric. All-null columns are labeled empty regardless of their dtype.
- Datetime-like is a descriptive label at >=95% successful parsing, not a schema guarantee; 80% successful dates mixed with other strings remain mixed. Month-first interpretation can be wrong for a particular source. Bare numbers and two-digit years are excluded. Native datetime columns are also datetime-like.
- ID evidence includes an `id`/`uuid`/`key` name token, a unit-step sequence among at least 20 distinct finite integer values, and median text length. These hints do not change the broad advisory flag, ranking, or score. Unique useful categories still trigger; the intended role is not established.
- Percentages are on a 0–100 scale; unique ratios are on a 0–1 scale. Undefined ratios use zero. Empty datasets receive a critical finding and score zero.

## Issue thresholds and ranking

Every issue includes type, column, severity, triggering statistic, exact value, detection threshold, ID, and rank. Higher-severity boundaries are inclusive.

Profile 1.2 also includes the severity assignment rule and observed evidence (counts, denominators, and IQR fences where applicable). Rates remain unchanged. The review status is derived from the highest detected severity rather than a score band. Fewer than 20 rows adds a context note, not another penalty. None of these thresholds are statistical significance tests.

| Issue | Detection | Low | Medium | High | Critical |
|---|---|---|---|---|---|
| Missingness | Missing percentage > 0 | < 5% | >= 5% | >= 20% | >= 50% |
| Duplicates | Duplicate percentage > 0 | < 2% | >= 2% | >= 10% | >= 30% |
| Outliers | IQR outlier percentage > 0 | < 1% | >= 1% | >= 10% | — |
| Constant | One distinct non-null value | — | — | Always | — |
| Near-constant | Top value >= 95%, not constant | — | Always | — | — |
| Possible ID | As defined above | Always | — | — | — |
| Mixed type | Mixed minority share > 0 | — | < 10% | >= 10% | — |
| Non-finite | Infinite numeric count > 0 | — | — | Always | — |
| Empty dataset | No rows or columns | — | — | — | Always |

Ranking: critical, high, medium, low; within a severity, ascending issue type then column name (dataset-level uses an empty name). Stable IDs and ranks are assigned after sorting. The UI shows the first five, plus an expandable complete list and column-specific warnings. Ranking does not infer business impact.

## Exact quality-score formula

Let `M` and `D` be missing-cell and duplicate-row fractions; `C` the number of columns; `K`, `N`, `I`, `T` the counts of constant, near-constant, possible-ID and mixed-type columns. Let `O` be the sum of outlier counts **only in numeric columns with outlier percentage >= 1%**, `F` the finite observation count across all numeric columns, and `B` the infinite-value count across columns. All divisions by zero return zero.

| Category | Penalty | Cap |
|---|---|---|
| Missingness | `30 * M` | 30 |
| Duplicate rows | `20 * D` | 20 |
| Outliers | `15 * min(1, 5 * O/F)` | 15 |
| Constant columns | `15 * K/C` | 15 |
| Near-constant columns | `5 * N/C` | 5 |
| Possible IDs | `3 * I/C` | 3 |
| Mixed types | `12 * T/C` | 12 |
| Non-finite values | `10 * B/(rows*C)` | 10 |

Each category penalty is rounded to six decimal places. **Score = round(max(0, 100 - sum(penalties)), 2)**. Empty datasets add a 100-point penalty. The non-finite category is an explicit additional check to prevent unusable infinities from being silently ignored. Constants and near-constants are mutually exclusive. Other categories can overlap. The score is a transparent heuristic, not a probability, statistical test, or certification of readiness.

Score policy remains 1.0. See the README for each weight's policy rationale, the 1% IQR scoring discontinuity, correlated penalties, and dilution by dataset width. These are uncalibrated choices. Neither a high score nor a lack of findings establishes validity or modeling readiness.

## V1 policy additions

Thresholds now live in `policy.py` and effective overrides are included in the profile. Every issue has evidence, a category and descriptive confidence. String-format warnings (blank, surrounding whitespace, case-folded variants) are low and unscored. See [CHECKS.md](CHECKS.md) for exact definitions and false-positive risks, and [SECURITY.md](SECURITY.md) for ingestion limits and encoding behavior. Run timestamps/duration remain outside the reproducible profile. Default score arithmetic remains policy 1.0.

## V1.1 numerical representation

Profile 1.3 preserves parsed integer min/max and adds precision notes beyond the float64 exact-integer range. Means/quantiles/IQR remain approximate. Native finite magnitudes over 1e150 are rejected rather than silently overflowing. See CSV_INFERENCE.md and SCORING_STRESS_TEST.md; default score policy remains 1.0.
