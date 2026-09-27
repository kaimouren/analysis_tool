# Validation evidence

## GitHub publication follow-up (2026-09-27 UTC)

The user supplied `https://github.com/kaimouren/analysis_tool.git`; it had no remote refs. GitHub credentials were available at this follow-up. The reviewed 80-file source archive was committed without the old local history and pushed as `6c6c5d24610cbc0830c0819eba5eb7ca137315f1` on `main`. No existing repository content was overwritten.

**Remote GitHub Actions: verified successful.** [Run 36290414830](https://github.com/kaimouren/analysis_tool/actions/runs/36290414830) completed with conclusion `success`. Observed successful steps include dependency installation, `pip check`, pytest, Ruff, synthetic evaluation, behavioral evaluation and scoring stress. This is actual GitHub-hosted Ubuntu/Python 3.11 execution, not an inference from local checks. Later documentation commits have their own runs shown in the repository Actions tab.

**Public Streamlit deployment: Not verified.** No hosted app URL is claimed. The earlier no-GitHub-auth / unverified-remote entries below describe the original local acceptance session and are superseded by this follow-up for GitHub only. Live-provider limitations remain unchanged.

## V1.2 release acceptance (2026-09-26 local / 2026-09-27 UTC)

Baseline `0f84ad2`: 81 tests passed in 10.25s and Ruff passed before changes. Application 1.2.0, profile schema 1.4, default score policy 1.0 unchanged. Current-source acceptance follows; older sections are historical evidence.

| Check | Actual V1.2 result |
|---|---|
| Windows 10, Python 3.11.3, pytest | **92 passed in 13.16s** |
| Windows Ruff / dependency consistency | **All checks passed / No broken requirements found** |
| Debian 12 under WSL, Python 3.11.2, pytest | **92 passed in 24.70s**, including Streamlit AppTest and outside-root sample resolution |
| Linux Ruff / dependency consistency / evaluations | **All checks passed / No broken requirements found / all three evaluation suites passed** |
| Linux server startup | **PASS**: started from `/tmp`, health endpoint returned `ok`, root returned HTML; not a Linux browser or public-host test |
| Synthetic evaluation | **8/8 cases; 11 expected findings, zero misses/extras** |
| Fictional export evaluation | **5/5 scenarios; 23 required observations, 5 explicitly ambiguous warnings, zero misses/extras** |
| Score stress | **10/10 exact score expectations** |
| Resource/concurrency rerun | **11/11 cases passed**; 2/5/10 callers matched sequential profiles and restored warning filters |
| Chrome browser smoke | **PASS**: messy/clean/malformed uploads, recovery, no-key guidance, chart, severity metrics, Markdown download |
| Screenshot review | `docs/demo.png` refreshed and visually checked: score and four severity counts visible, high-priority banner above score |
| Source credential/private-path scan | **80 deliverable files, zero matches** against common key/private-key patterns, configured credentials and developer home-path patterns |
| GitHub repository / remote Actions | **Not verified**: no remote, CLI, token or usable noninteractive GitHub credential; no push or workflow execution |
| Public Streamlit deployment / URL | **Not verified**: no authenticated deployment access; no public URL exists from this work |
| Live provider smoke | **Attempted; successful generation Not verified.** One synthetic aggregate request returned rejected output (`llm_failed`, reason `validation`); deterministic fallback worked |

The 11 added test cases exercise high aggregate score with a critical finding in the profile/UI/report; six lexical representation families without changing findings; leading-zero preservation in bounded examples; sample size/window/privacy bounds; actual UI fallback/generated labeling; and launching the bundled sample outside the repository working directory. Existing tests cover oversize/empty/malformed input, warning restoration, configuration precedence, numerical boundaries and provider failures. Mutation evidence remains the five V1.1 controlled defects; it was not relabeled as a new mutation experiment.

### Commands and environments

Windows used the existing isolated `.venv-v1-1` (Python 3.11.3, pandas 2.3.3, NumPy 2.4.6). Commands, from the repository root:

```powershell
.venv-v1-1/Scripts/python -m pytest -q
.venv-v1-1/Scripts/python -m ruff check .
.venv-v1-1/Scripts/python -m pip check
.venv-v1-1/Scripts/python benchmarks/benchmark.py --output benchmarks/v1-2-results.json
$env:OPENAI_API_KEY='' # Clear only this shell/process environment for the no-key browser run.
$env:OPENAI_BASE_URL=''
.venv-v1-1/Scripts/python -m streamlit run app.py --server.headless true --server.port 8501
# Set CHROME_PATH to the locally installed Chromium executable.
.venv-v1-1/Scripts/python tests/browser_smoke.py
# Separately, in a shell with the provider configuration still available:
.venv-v1-1/Scripts/python tests/live_llm_smoke.py
```

The evaluation functions from `evals/run.py`, `evals/behavioral.py` and `evals/stress.py` were called together, asserting all three `passed` flags. Their equivalent standalone commands are in README. Each of the 11 named `benchmarks/adversarial.py CASE` workers ran in a fresh subprocess; combined results are saved separately as `benchmarks/v1-2-adversarial-results.json`, preserving V1.1 artifacts. The live-provider command exited 1 intentionally because rejected output is not successful provider verification. No response body or credential was logged.

Linux verification used the installed Debian 12 WSL distribution (kernel `4.4.0-19041-Microsoft`, glibc 2.36), with source on the Windows-mounted filesystem. Since the distribution had no Python installed, Debian Python 3.11.2 packages were extracted into ignored `.linux-runtime/runtime`, and fresh Linux wheels were installed into `.linux-runtime/packages`. No system packages were installed. Versions: pandas 2.3.3, NumPy 2.4.6, Streamlit 1.64.0. Native Linux binaries, not the Windows interpreter, ran the checks. This is local WSL evidence, not a Community Cloud image or a case-sensitive-filesystem portability guarantee.

The isolated launcher set `PYTHONHOME` to `runtime/usr`, `LD_LIBRARY_PATH` to the extracted Linux library directories, and `PYTHONPATH` to the isolated Linux packages and bundled pip wheel. It ran `python -m pytest -q`, `python -m ruff check .`, `python -m pip check` and the three evaluation functions with success assertions. Wheels were fetched with `pip download --only-binary=:all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --platform manylinux_2_27_x86_64 --python-version 3.11 --implementation cp --abi cp311 -r requirements-dev.txt`, then installed offline with `pip install --no-index --find-links WHEELS --target PACKAGES -r requirements-dev.txt`. Slow direct WSL downloads were cancelled before switching to this route.

The Linux HTTP smoke started `python -m streamlit run APP_PATH --global.developmentMode false --server.headless true --server.port 8502 --server.address 127.0.0.1` from `/tmp`, with provider credentials cleared, then terminated the test server after checking health and HTML. The first startup attempt failed because Streamlit inferred development mode from the nonstandard `--target` directory; explicitly disabling it resolved that test-environment issue. No application workaround was added. The conventional virtual-environment Quickstart remains the supported user path.

### Performance and lock decision

Core 500 / 10,000 / 100,000-row runs took **0.0446 / 0.1865 / 1.5487 seconds**, sampled peak RSS **76.80 / 82.22 / 126.20 MiB**. Two / five / ten simultaneous distinct 10,000-row callers took **0.4765 / 1.1712 / 2.4264 seconds** wall time, sampled peak RSS **86.48 / 94.96 / 98.45 MiB**. All profiles matched sequential fingerprints, retained their own column names, restored warning filters, created no files and made zero provider calls. Background Linux dependency setup was active during these single runs; numbers are observations, not an isolated speed comparison, latency distribution or hosting-capacity guarantee.

The lock remains unchanged after a temporary trace found warning contexts throughout pandas dtype conversion, index construction, comparison, median and quantile operations. On Python 3.11 these share process-global `warnings.filters`; a narrow CSV/date lock does not cover them. See `docs/CONCURRENCY.md` for the correctness/throughput tradeoff and limits of protection.

### Release and remaining uncertainty

The current snapshot has portable application/asset paths and no matching developer home paths. Earlier local Git history retains historical machine-path examples. A history-free tracked-source ZIP under `.release/data-qa-agent-v1.2.0.zip` is the publication handoff; do not push the old local history unchanged. `.env`, Streamlit secrets, runtime/package directories, generated reports and the archive directory are ignored. Pattern scanning is bounded evidence, not a formal secret-free guarantee.

Manual GitHub publication, actual Actions verification and Community Cloud deployment steps are in `docs/DEPLOYMENT.md`. No remote success is implied by local Linux or browser results. CSV inference remains lossy; raw samples cover only early records. Generated prose has no semantic-verification guarantee. Per-input limits do not bound total host memory or visitor spending, and serialized callers are not production multi-user load validation. These are documented limitations, not silently completed work.

## V1.1 adversarial acceptance (2026-09-26 local / 2026-09-27 UTC)

Baseline commit: `dca9d03`. Baseline rerun: **56 passed in 12.98s**, Ruff passed. Implementation/evidence checkpoint: `7ba92f6`. App version 1.1.0; profile 1.3; default score policy 1.0 unchanged. Historical V1 evidence follows below.

### Final results

| Check | Actual result |
|---|---|
| Fresh environment, working source pytest | **81 passed in 19.98s** |
| Fresh local checkout pytest | **81 passed in 15.28s** |
| Ruff / pip check in fresh checkout | **All checks passed / No broken requirements found** |
| Synthetic regression | **8/8 datasets; 11/11 expected findings** |
| Fictional export behavioral coverage | **5/5 scenarios; 23/23 required observations; 5 explicitly ambiguous warnings; 0 extras; 0 misses** |
| Score stress | **10/10 exact score expectations** |
| Threshold probes | **40 isolated band probes and 52 actual-frame curves recorded** |
| CSV representation probes | **11 cases recorded and key transformations regression-tested** |
| Resource/concurrency harness | **11/11 cases passed**, including safe wide/huge-cell rejection and 2/5/10 simultaneous callers |
| Controlled test mutations | **5/5 killed by assertion failures**, not import/collection crashes |
| Real Chrome smoke from fresh checkout | **PASS**: clean/problematic/malformed uploads, no-key guidance, chart, Markdown download |
| Credential scan | **76 deliverable files checked; no common credential-pattern/current-key matches** |

The 44-question review moved from **18 PASS / 18 WEAK / 4 FAIL / 4 OUT OF SCOPE** to **33 PASS / 7 WEAK / 0 FAIL / 4 OUT OF SCOPE**. The unchanged weaknesses and grading rationale are explicit in `docs/V1_1_RED_TEAM.md`. Counts are review judgments, not accuracy measurements.

### Fresh-install / checkout commands actually used

From the repository root in PowerShell:

```powershell
.venv-clean/Scripts/python -m venv .venv-v1-1
.venv-v1-1/Scripts/python -m pip install -r requirements-dev.txt --index-url https://pypi.org/simple --quiet --disable-pip-version-check
.venv-v1-1/Scripts/python -m pytest -q
.venv-v1-1/Scripts/python -m ruff check .
.venv-v1-1/Scripts/python -m pip check
git clone --local --no-hardlinks . .validation-v1-1
```

The new environment has `include-system-site-packages = false`; packages were installed from the declared requirements, not copied from another environment. The clone contains committed source and fixtures only; its requirements match those installed. The environment lives outside the checkout but inside the ignored repository workspace. No global application/test packages were used. Initial local clone encountered a Windows sandbox signal-pipe error; explicit local cloning with the needed process permission succeeded. No network remote was cloned.

From `.validation-v1-1`:

```powershell
../.venv-v1-1/Scripts/python -m pytest -q
../.venv-v1-1/Scripts/python -m ruff check .
../.venv-v1-1/Scripts/python -m pip check
../.venv-v1-1/Scripts/python benchmarks/benchmark.py --output benchmarks/fresh-checkout-results.json
$env:OPENAI_API_KEY=''
$env:OPENAI_BASE_URL=''
../.venv-v1-1/Scripts/python -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501
```

In a second terminal, `CHROME_PATH` was set to the local Chrome executable and `../.venv-v1-1/Scripts/python tests/browser_smoke.py` passed. The screenshot was visually inspected and copied to `docs/demo.png`; the benchmark artifact was copied to `benchmarks/v1-1-results.json`. The local source app was restarted after checkout verification.

The checkout also executed the actual `run()` functions from `evals.run`, `evals.behavioral` and `evals.stress`, asserting each `passed` value. Equivalent standalone commands are `python evals/run.py`, `python evals/behavioral.py`, and `python evals/stress.py`. In the source checkout, `python evals/sensitivity.py`, `python evals/inference.py`, `python benchmarks/adversarial.py` and `python tests/mutation_check.py` generated the committed evidence. All calls used the isolated environment interpreter.

### Performance and concurrency

Final fresh-checkout core benchmark, eight columns, Windows/Python 3.11.3/pandas 2.3.3/NumPy 2.4.6/eight logical CPUs:

| Rows | Core seconds | Sampled peak RSS MiB |
|---|---:|---:|
| 500 | 0.0624 | 76.43 |
| 10,000 | 0.1938 | 82.11 |
| 100,000 | 1.6488 | 128.06 |

RSS sampling is every 5 ms, process totals include imports/input, and core timing excludes CSV parsing. The separate resource harness includes ingestion: 100,000-row mixed strings took 2.8799s / 129.36 MiB peak; 100 approximately-60,000-character cells took 0.39s / 147 MiB. Simultaneous four-column 10,000-row callers took **0.6374s / 86.17 MiB (2)**, **1.4846s / 95.41 MiB (5)**, and **3.2652s / 98.55 MiB (10)** for the batch. These are single-run in-process proxies, not browser/hosting capacity or latency percentiles. No provider calls were made in load tests.

The first concurrency experiment found leaked global warning filters despite matching outputs. Locking only explicit parser warning contexts was insufficient. The full public-entry lock fixes the tested interference by serializing analysis. Final runs match sequential profile fingerprints, restore filters, retain each caller's own data label and create no files in an empty working directory. Queued uploads and retained Streamlit results can still exhaust memory; no admission limit or paid-API quota exists.

### CI and security evidence boundaries

The workflow now declares Python 3.11, read-only repository permissions, dependency install/check, pytest, Ruff, synthetic evaluation, behavioral evaluation and score stress. A local structural check verified the expected commands, indentation and runner/permissions. It is not a complete GitHub workflow-schema validator. The declared checks ran locally in the clean checkout; **no remote GitHub Actions or public deployment result is claimed**.

The scoped secret scan checked common OpenAI/GitHub/private-key patterns and the current configured key without printing credentials. It is not a comprehensive secret detector, dependency vulnerability audit or penetration test. Mocked adversarial model outputs expose both newly rejected phrases/schema defects and still-accepted paraphrased falsehoods. No live model request or explanation-quality benchmark was added. New docs document score overlap/dilution, parser representation loss, numerical precision, concurrency/resource limits, deployment caveats and the five actual mutation kills.

## V1 completion validation (2026-09-26 local / 2026-09-27 UTC)

The V1 audit started from `38d4aef`, with **31 passing baseline tests**. Historical sections below describe earlier passes, not the current suite. V1 keeps score policy 1.0 and moves the profile to 1.2; the planted sample remains **92.36** with nine detected findings.

### Fresh installation and automated checks

Created a separate `.venv-clean` using Python 3.11.3 and installed `requirements-dev.txt` (which includes runtime requirements) from PyPI. Installation exited successfully. Pip emitted a version-check warning after installation; `pip check` independently reported no broken requirements. No packages were copied from the previous environment.

Commands were run with `.venv-clean/Scripts/python` on Windows:

| Check | Actual result |
|---|---|
| `-m pytest -q` | **56 passed in 10.72s** |
| `-m ruff check .` | **All checks passed** (fatal syntax/name/import rules, not a type-check claim) |
| `-m pip check` | **No broken requirements found** |
| `evals/run.py --output evals/results.json` | **8/8 datasets passed; 11/11 expected findings; zero missed/unexpected findings; all expected scores matched** |
| `git diff --check` | No whitespace errors; Git only noted CRLF-to-LF normalization |

Primary installed versions: Streamlit 1.64.0, pandas 2.3.3, NumPy 2.4.6, Plotly 6.9.0, Pydantic 2.13.5, OpenAI 2.54.0, pytest 9.1.1, Ruff 0.16.9, psutil 7.2.2. Broad constrained dependencies remain intentional; this is one verified resolution, not proof for every allowed version. CI now includes tests, lint and evals; no remote GitHub Actions run or public deployment is claimed.

New tests exercise strict duplicate/blank headers, binary and malformed CSV, unsupported types, row/width/cell/frame guards, Unicode/Latin-1/default nulls, inclusive severity neighbors, concentration/uniqueness boundaries, policy overrides, advisory string counts, five scoring scenarios, size-normalized missingness, metadata/profile separation, all-issue report guidance, safe chained failures, log-field rejection, endpoint egress controls and mocked LLM success/numeric rejection/timeout. The existing 500-row and edge-case UI regression coverage remains active. Two initial new-test assumptions were corrected: ranking put duplicate rows before the low missingness finding, and the logger intentionally rejects rather than silently drops unknown fields.

### Evaluation and performance

The [eight-case evaluator](evals/README.md) round-trips CSV ingestion and compares independently authored issue type/column/severity tuples and hand-computed scores. [Recorded results](evals/results.json) contain timings and exact findings. Zero synthetic extras is not a population false-positive estimate.

The [benchmark](benchmarks/benchmark.py) measured one fresh process per size on Windows/Python 3.11.3 with eight logical CPUs, pandas 2.3.3 and NumPy 2.4.6, eight mixed columns and seed 42. Input construction is excluded. RSS is sampled every 5 ms and includes interpreter/import/input memory; it can miss short-lived peaks.

| Rows | Profile seconds | Sampled peak RSS MiB | Incremental peak MiB |
|---|---:|---:|---:|
| 500 | 0.0427 | 76.88 | 1.79 |
| 10,000 | 0.1788 | 82.58 | 5.89 |
| 100,000 | 1.5231 | 136.16 | 36.27 |
| 500,000 | 14.1246 | 374.10 | 176.46 |

Commands: `.venv/Scripts/python benchmarks/benchmark.py --output benchmarks/results.json` and `... benchmarks/benchmark.py --rows 500000 --output benchmarks/extended-results.json`. The extended case explicitly increases benchmark-only row/cell guards. **500,000 rows are not a supported UI upload.** No end-to-end latency, concurrency, percentile or enterprise-scale claim follows from these single runs. Full measurements and environment metadata are committed.

### Real browser and report export

Restarted Streamlit from `.venv-clean` on `127.0.0.1:8501`, with `OPENAI_API_KEY` and `OPENAI_BASE_URL` empty. Ran headless Chrome through `tests/browser_smoke.py` using `CHROME_PATH`:

- Uploaded the actual 500-row problematic CSV; observed score 92.36, offline guidance and Plotly output.
- Downloaded the actual Markdown report; confirmed findings, recommendations and no-API status.
- Uploaded a clean numeric CSV; observed no findings under the implemented rules.
- Uploaded malformed quoted input; observed an actionable parser error, no traceback and no stale report download.
- Refreshed and visually inspected `docs/demo.png` using synthetic sample data.

AppTest separately covers header-only, all-null, infinite-only, one-row, categorical and clean datasets. Provider behavior is mocked in automated tests; no live provider request was required or made during this V1 pass. Prior live-call evidence remains historical below.

### Security review and scope

Scanned all 48 then-current tracked/untracked deliverable files (excluding binary images from content matching) for common OpenAI/GitHub/private-key credential patterns: no matches. Scanned both existing Git revisions for those patterns and the current configured key: no matches. No `.env` or `secrets.toml` is tracked. Reviewed the filename-as-label path, Markdown escaping, plain-text provider rendering, aggregate-only API allowlist and server-controlled endpoint allowlist. This is a scoped repository review and pattern scan, not a penetration test, dependency vulnerability audit or proof of absence of every possible secret.

V1 boundaries and remaining risks are explicit in [SECURITY.md](docs/SECURITY.md): no authentication/rate limiting or multi-user load validation, aggregate scores remain uncalibrated, parsing can alter raw tokens, Latin-1 cannot prove encoding, provider prose can be wrong, and host resource/retention controls remain deployment responsibilities. The [interview guide](docs/INTERVIEW_GUIDE.md) answers all thirty requested questions; three ADRs record the key decisions.

## Hardening pass

On 2026-09-26, the pre-change baseline passed **17 tests**. The skeptical review then reproduced a Plotly crash for both all-null columns and header-only CSVs, which the baseline suite had not exercised through the UI. The fixes and review decisions are recorded in [docs/REVIEW.md](docs/REVIEW.md).

After hardening, `pytest -q` passed **31 tests**. Added regression coverage includes:

- 99 clean columns plus one entirely missing column: score remains 99.7, but review status is critical and worst-column missingness is 100%.
- Clean numeric synthetic data: score 100, no findings, explicit non-certification language.
- All-null, header-only, infinite-only, one-row, categorical-only, and clean numeric UI cases: no exceptions; report download remains available; absent observations produce a message instead of an empty/broken chart.
- Mixed string tokens (`00123`, `1`, `1.5`, `N/A`, `unknown`, currency, percentage), strict parser counts, and the separate effects of pandas CSV inference.
- Ambiguous dates, excluded two-digit years, 80% vs 95% date success, and native datetime columns.
- High-cardinality name/sequence hints without asserting a key role.
- Explicit severity rules, fact/interpretation report content, bounded local evidence excluded from LLM payloads, source preservation, and repeated JSON equality.
- The deliberately skewed numeric probe retains score 89.5; a one-row numeric probe retains 82; the bundled sample retains 92.36. These values illustrate policy behavior, not verified real-world data quality.

The core suite also checks empty DataFrames, constant/near-constant flags, duplicates, encodings, and provider failures. Score policy 1.0 is unchanged. Profile 1.1 adds descriptive evidence and cautious semantic labels.

An additional comparison loaded the pre-hardening `qa_core.py` from Git and compared seven datasets (sample, all-null, header-only, one-row, mixed strings, skewed numeric, and clean numeric). Scores, penalty breakdowns, issue existence, severity, triggering values, and ranking matched the baseline exactly. Added metadata and descriptive semantic labels were intentionally excluded from that compatibility comparison.

The restarted Streamlit server passed the real headless-Chrome upload/chart/offline-report smoke test, and `docs/demo.png` was refreshed. An initial run against the already-running development server encountered a stale imported module; restarting loaded the new modules successfully. Browser checks use the sample; the edge datasets use Streamlit AppTest.

One live explanation call was made during this hardening pass with the existing environment configuration and `gpt-4o-mini`. It returned validated structured output. No raw examples or column names were sent, and no response body or credential is committed. This does not verify arbitrary providers or factual correctness of generated prose.

The sections below retain the earlier deployment-preparation evidence and environment details; their test counts refer to that earlier pass.

Validated on 2026-09-26 using Windows, Python 3.11.3, and a project-local virtual environment. Runtime dependencies were installed in that environment during the initial build; the polishing pass reconciled runtime and development dependencies. This was not a fresh Linux install.

| Dependency | Version exercised |
|---|---|
| Streamlit | 1.64.0 |
| pandas | 2.3.3 |
| NumPy | 2.4.6 |
| Plotly | 6.9.0 |
| Pydantic | 2.13.5 |
| OpenAI SDK | 2.54.0 |
| pytest | 9.1.1 |

## Automated checks

Commands below assume the project environment is activated and the current directory is the repository root.

```bash
python -m unittest discover -s tests -v  # baseline before polishing: 11 passed
pip install -r requirements-dev.txt
pytest -q                              # after polishing: 17 passed
python -m pip check                    # no broken requirements
```

Tests cover hand-calculated missingness, duplicate denominators, IQR counts, score penalties, threshold boundaries, sample coverage, repeatability, preservation of the source DataFrame, empty/all-null/one-column/non-numeric data, encoding fallback, malformed CSV errors, nullable dtypes, mocked API failure/success, and rejected output. Deployment tests cover configuration precedence, absent secrets, Streamlit secrets, the upload limit before parsing, and isolation of server credentials from widgets and visitor-controlled endpoints.

Streamlit AppTest exercised the sample toggle and both numeric and categorical explorer selections. No app exceptions occurred. The AppTest runner emits an expected missing-ScriptRunContext warning outside a live server.

A second run exported only the staged Git tree into a fresh temporary checkout and ran `python -m pytest -q` there with the existing environment: **17 passed**. This checks that ignored local files are not needed to run the suite; it does not verify a fresh dependency installation.

## Sample results

| Result | Observed |
|---|---|
| Rows / columns | 500 / 9 |
| Missing cells | 186 (4.133333333333333%) |
| Duplicate rows after first occurrence | 20 (4%) |
| Quality score | 92.36 |
| Detected categories | missingness, duplicates, outliers, constant, near-constant, possible ID, mixed type |

These results match the pre-polish baseline. The automated suite also compares repeated profile JSON and verifies that the input DataFrame is unchanged.

## Browser and runtime checks

Started the server with API environment variables empty:

```bash
streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501
python tests/browser_smoke.py
```

The browser script discovers Chromium on PATH or uses `CHROME_PATH`. The Windows validation supplied that variable locally; no machine-specific path is committed. Headless Chrome required execution outside the tool sandbox; the restricted attempt could not open its debugging endpoint.

The successful browser run:

- Uploaded `examples/messy_sample.csv` through the actual file input.
- Observed dataset metrics and the no-API explanation message.
- Confirmed a rendered Plotly chart.
- Downloaded the Markdown report and verified its summary, guidance, and fallback status.
- Captured `docs/demo.png`, which was visually inspected.

The restarted server loaded the 10 MiB upload setting. Its console showed no application errors during the successful run. The size-rejection path was tested directly before CSV parsing; an oversized file was not uploaded through Chrome.

## Live LLM smoke test

```bash
python tests/live_llm_smoke.py
```

One small request was made using the available environment configuration and the default `gpt-4o-mini` model. It returned a valid structured explanation that passed the application's validation. Only synthetic aggregate findings were sent. No credentials, private endpoint, or response body are included here.

This verifies one configured provider/model combination, not every OpenAI-compatible service. Mocked failures and invalid outputs verify graceful fallback without changing deterministic results. The live request was made through the helper, not the browser's AI button.

## Public-file hygiene

Reviewed the candidate public file set for API-key prefixes, credential assignments, token/password-like literals, environment credential values, personal usernames, and Windows absolute paths. No sensitive matches were found. The original browser helper's fixed Windows installation path was replaced with browser discovery and an environment override. The screenshot contains only synthetic data and an empty API-key widget.

Checked Git ignore behavior for virtual environments, caches, environment files, Streamlit secrets, temporary uploads, generated reports, and the older local browser screenshot. Source, tests, the sample CSV, documentation, and the curated demo image remain included. This is a targeted scan and review, not a guarantee against all possible secret formats.

## Not yet verified

- Streamlit Community Cloud deployment and resource behavior under concurrent users.
- GitHub-hosted CI on Ubuntu; a Python 3.11 workflow is included but has not run remotely.
- Every dependency version allowed by the declared ranges.
- Browser interaction with the AI-generation button and arbitrary third-party endpoints.
- Large-file performance beyond the explicit input-size guard.
