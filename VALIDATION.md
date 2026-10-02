# Validation evidence

## V2.2 agent evaluation acceptance (2026-10-02)

Baseline: published `27a58f6`, tree-equivalent local `465d83c`, 224 existing tests.
No analytics tool or dependency was added. Production prompt remains planner-v2.1.

| Check | Observed result |
|---|---|
| Windows / Python 3.11.3 | **272 passed in 26.02s**, including **48 V2.2 tests** |
| Debian / Python 3.11.2 | **272 passed in 23.46s** |
| Ruff / dependency consistency | Passed on both platforms |
| Existing evals | **8/8, 5/5, 10/10, 24/24**, unchanged **36/36 scripted investigation scenarios** |
| Full real-model capture | **108/108 terminal captures**, 36 scenarios × 3 repeats; **21 successful** |
| Candidate prompt capture | **36/36 terminal captures**, 12 golden scenarios × 3 repeats |
| Budget experiment | **12/12 terminal captures**, 2 scenarios × 3 repeats × 2 budgets |
| Offline baseline replay | Windows and Linux passed, without API calls |
| Credential/private-path scan | **143 files, zero matches**; heuristic patterns plus configured-key matching |
| Remote V2.2 Actions | **Verified successful** for `af42718`: [run 37000303082](https://github.com/kaimouren/analysis_tool/actions/runs/37000303082), including saved-baseline replay |
| Optional paid GitHub workflow | Implemented; not manually executed on GitHub in this pass |
| Public app deployment | Not verified |

Published on existing `main` history without force push: `d8904bd` prompt/telemetry,
`afad134` benchmark/evaluator/tests, `af4fb52` measured artifacts and CI,
`af42718` release documentation. Publication and locally validated file trees
matched exactly. GitHub-hosted Ubuntu/Python 3.11 passed all tests, lint,
dependency checks, five existing eval suites and `evals.benchmark_ci`, including
replay of four experiment artifacts and detection of the known candidate
critical regression. Subsequent documentation commits have their own Actions runs.

All **156 new real investigations** used synthetic fixtures, requested
`gpt-4o-mini` at `api.openai.com`, three concurrent workers, temperature omitted
(provider default), no SDK retries, 15-second request timeout and a soft
120-second overall deadline. Normal limits were eight steps/eight calls/three
errors. Full capture began **2026-10-02 10:49:32 UTC**. A completed capture is a
recorded terminal outcome, not necessarily a successful task. The golden baseline
reuses the corresponding full-suite runs; it is not another 36 paid runs.

### Real-model observations

| Full baseline metric | Value |
|---|---:|
| Scenario Success Rate | **4/36 = 11.11%**, all three repeats pass |
| Run Success Rate | **21/108 = 19.44%** |
| Tool Selection Accuracy / Argument Validity | **69.01% / 93.32%** |
| Evidence Grounding / Coverage | **100% / 43.67%** |
| Unsupported / Contradicted Claim Rate | **0% / 0%**, 255 supported claims |
| Recovery Rate | **37.93%**, macro mean across 29 runs with errors |
| Premature Stop / Redundant Tool Rate | **54.63% / 2.17%** |
| Average calls / successful calls | **2.81 / 2.30** |
| Stop Accuracy | **26.85%** |
| Mean / median latency | **15.61s / 15.13s** |
| Average input / output tokens | **12,107 / 201.03**, 103 runs with complete available usage |
| Estimated cost | **Unavailable**; no pricing inferred |

Four scenarios passed 3/3, six were mixed and 26 passed 0/3. Unstable scenarios:
`conversion_device` 2/3, `missingness_increase` 1/3, `duplicate_increase` 2/3,
`weak_names` 1/3, `missing_year` 2/3 and `recover_wrong_date` 1/3. Reports retain
mean/min/max/population standard deviation, denominators and path variance.

Golden prompt A/B: success **8/36 → 11/36** (+8.33 pp), but critical
`conversion_device` regressed **2/3 → 1/3**. The gate **failed**; no prompt was
promoted. Budget probe: **0/6 success at both four and eight steps**; calls
2.83 → 3.00, latency 19.24s → 19.51s, premature stops 5/6 → 6/6; one four-step
run timed out. These small experiments do not establish a causal prompt/budget effect.

### Evaluation, taxonomy and regression policy

Layer 1 remains scripted controller/tool regression and does not measure model
accuracy. Layer 2 uses real repeated decisions and deterministic offline scoring,
without an LLM judge. Each scenario specifies evidence, scope, accepted classes,
status and budget. Six recovery probes inject one disclosed failure before real
model decisions; forced calls are excluded from model-selection/argument
denominators but included in recovery/call budgets. Independent tool replay catches
forged answer/ledger pairs. Provenance and task coverage are scored separately.

Overlapping failure counts: incomplete answer **79**, missing required evidence
**64**, premature stop **59**, unexpected status **54**, wrong tool **42**,
unrecovered error **18**, wrong arguments **17**, repeated call **7**, timeout **5**.
Provider failures remain in success denominators. Empty-claim runs do not inflate
grounding, and unknown final-request usage is excluded from token averages.

The [saved baseline](benchmarks/baselines/investigation-v2.2/summary.md) preserves
failures. Unsupported/contradicted claims, altered tool evidence and grounding
below 99% fail safety gates. Any critical scenario losing a successful repeat
fails. Other adverse changes use max(5 pp, twice measured baseline standard error):
run success **7.62 pp**, scenario success **10.48 pp**, coverage **9.28 pp**,
argument validity **5 pp**, recovery **18.02 pp**, premature stops **9.58 pp**.
These are operational tolerances, not significance tests. Lesser changes and
undefined denominators are warnings; configuration differences are informational.

Standard CI replays saved artifacts against pinned scores and confirms the known
candidate critical regression remains detectable, with no external model calls.
A separate manual workflow accepts model, repeats, suite, prompt and subset and
uploads synthetic artifacts. Frozen replay cannot measure a new planner's
decisions; future prompt/provider changes need fresh real runs.

### Red-team and limitations

Tests cover malformed/missing/duplicate artifacts, impossible metrics, altered
evidence, wrong scopes, equivalent repeated calls, premature stops, recovery,
claim classification, partial capture, timeouts, incompatible versions, missing/
stale baselines, and aggregate improvement hiding critical regression. Initial
Linux replay exposed platform-dependent CSV fingerprint line endings; explicit
canonical CRLF hashing fixed it without changing data or recorded actions.
Ambiguous-task error limits now cannot count as clarification; injected test
planners cannot be mislabeled as real execution. No reasoning or credentials are saved.

Real-model benchmark results are model-, prompt-, provider-, and
configuration-specific and should not be interpreted as universal agent accuracy.
Three repeats, synthetic tasks, narrow scope selectors, accepted-class policy,
an unpinned model alias and concurrent provider calls limit generalization.
See [metric definitions and commands](docs/AGENT_EVALUATION.md) and the
[case study](docs/AGENT_RELIABILITY_CASE_STUDY.md). V2.2 completes the current
portfolio scope; no V3 work was started.

## V2.1 Investigation Agent acceptance (2026-10-02)

Baseline was the unchanged 158-test V2 tree, identical to published `8ab606f`.
Application version is now 2.1.0; profile 1.4, score 1.0 and comparison 2.0 remain
unchanged. No dependency was added. Existing architecture/tests/eval expectations
were retained.

| Check | Observed result |
|---|---|
| Windows / Python 3.11.3 | **224 passed in 23.06s**, 158 existing + **66 V2.1** |
| Debian / WSL / Python 3.11.2 | **224 passed in 21.36s** |
| Ruff / pip consistency | Passed on Windows and Linux |
| Existing eval suites | **8/8 synthetic, 5/5 behavioral, 10/10 stress, 24/24 comparison** |
| Investigation regression | **36/36 scenarios**, actual controller/tools with scripted planners |
| Real Chrome | V1/V2 workflows and V2.1 upload/question/consent/no-key-disabled workflow passed |
| Streamlit AppTest | Actual controller plus injected planner: consent, citations, trace, JSON export, input reset and generic failure checks passed |
| Synthetic real provider, short budget | **Partial**, 4 steps, 3 calls, 2 validation errors, 30.203s; precise error types not retained |
| Synthetic real provider, default budget | **Completed**, 3 planning steps, 3 calls including schema, 0 errors, 22.031s |
| Public deployment | **Not verified**; no public app URL claimed |
| V2.1 remote Actions | **Verified successful** for `bf05abe`: [run 36995675897](https://github.com/kaimouren/analysis_tool/actions/runs/36995675897), including investigation evals |
| Deliverable credential/private-path scan | **107 files, zero matches**, common patterns plus exact configured credentials; heuristic, not proof of absence |

The first Linux command used an incorrect distro alias and did not run; querying
installed distributions identified `Debian`, where the checks above passed. The
isolated interpreter/packages run against the Windows-mounted source, so this is
not a case-sensitive-filesystem or Community Cloud image test.

V2.1 was published as four logical commits on the existing public `main` history:
`758258f` engine/tools, `c50c980` UI, `5de54e5` tests/evals/CI, and `bf05abe`
documentation. No force push or old-commit rewrite. The publication tree matched
the local validated source tree exactly. GitHub-hosted Ubuntu/Python 3.11 ran
pytest, lint, dependency consistency and all five eval scripts successfully.
The missing-category follow-up fixes literal `"None"` matching and reran the
full Windows/Linux checks recorded above; subsequent commits have separate runs
in [Actions](https://github.com/kaimouren/analysis_tool/actions).

### Agent behavior metrics

Recorded artifact: [evals/investigation-results.json](evals/investigation-results.json).
This is an authored regression corpus, **not an independent live-planner accuracy
study**. The two real-provider runs above are separate, small observations.

| Metric | Measured value |
|---|---:|
| Task Success | 36/36 = 100% |
| Tool Selection Accuracy | 36/36 = 100% (scripted analysis-class coverage) |
| Tool Argument Validity | 98/101 = 97.03% |
| Evidence Grounding | 102/102 = 100% |
| Unsupported Claim Rate | 0/102 = 0% |
| Recovery Rate | 8/8 = 100% |
| Efficiency | 36/36 within scenario budgets; mean 2.81 calls |
| Stop Accuracy | 36/36 = 100% |

Typed argument validity includes deliberate malformed/unknown calls; existence
and dtype checks are separate runtime validations. Grounding is exact claim-to-
ledger provenance, not natural-language semantic correctness. Expected guarded
partial/failed outcomes count as successful test cases. Tests separately reject
invented output/citations, forged evidence, hidden reasoning, unsupported
causality/significance, premature finish, conflicting-evidence omission, repeated
tools and unsafe executable arguments. Every scenario must pass CI, with a 96%
minimum typed-argument validity threshold; answer wording is not compared.

### Tool trust model and limits

The model selects typed tools and evidence IDs; it cannot author accepted final
prose, access the DataFrame, execute expressions, inspect secrets or write files.
Each claim comes from deterministic evidence, with named columns and group values
grounded by actual data. Primary findings are automatically included even if the
model omits them. Directional premises use narrow sign/keyword checks, and why
questions require a decomposition matching the first eligible period comparison
unless that anchor's premise is contradicted. These checks do not prove arbitrary
question interpretation or business semantics.

Bootstrap schema, attempts, steps, errors, groups, output and context are bounded.
Exact repeated calls do not reexecute. Per-request timeout is 15 seconds with no
SDK retries; the overall 120-second deadline is soft. Result status honestly
distinguishes completed/partial/failed. No-key mode has no fabricated agent.

Untrusted cells are not forwarded as rows. Explicit UI consent covers real schema,
question and bounded group aggregates; those may still reveal sensitive facts.
The controller deep-copies planner context, discards free-form model prose and
records observable actions only. No long-term investigation history or hidden
reasoning logs. Valid but irrelevant analyses, model distraction by labels,
ambiguous questions, rate semantics, tiny groups, sampled population bias and
floating-point approximations remain limitations.

Read [tool contracts, evidence schema, formulas and exact metric definitions](docs/INVESTIGATION.md)
and [red-team findings/fixes](docs/V2_1_RED_TEAM.md). Run all checks with the Testing
commands in README; new targeted commands are:

```bash
python -m pytest tests/test_investigation.py tests/test_investigation_ui.py -q
python evals/investigation.py --output evals/investigation-results.json
# Optional real-provider requests using environment credentials:
python tests/live_investigation_smoke.py
```

CI adds `python evals/investigation.py` after existing suites. Local, configured
and remotely observed CI results are reported separately.

## V2 baseline comparison acceptance (2026-10-02)

Baseline: existing local V1.2 snapshot matched the published `d565180` tree. Before V2, **92 tests passed in 18.92s**, Ruff passed, and the remote branch was inspected without rewriting history. Application 2.0.0 adds comparison schema 2.0; V1 profile 1.4 and score policy 1.0 remain unchanged. No package dependency was added.

| Check | Observed result |
|---|---|
| Windows 10 / Python 3.11.3 full suite | **158 passed in 18.54s**: 92 existing tests + 66 V2 cases |
| Debian 12 / WSL / Python 3.11.2 full suite | **158 passed in 34.94s** |
| Ruff and `pip check` | Passed on Windows and Linux |
| Existing synthetic / behavioral / score evals | **8/8, 5/5, 10/10**, unchanged expectations |
| New V2 structured evals | **24/24**, including negative controls and direction/JSON invariants |
| Real Chrome smoke | Passed V1 and V2 uploads, no-key mode, charts (V1), baseline/current direction, comparison drift, Markdown downloads, malformed-input recovery and stale-download clearing |
| Provider boundary | Mocked valid/rejected/failing calls passed; **V2 live provider: Not verified**, no paid V2 call made |
| Public Streamlit deployment | **Not verified**; no tested public URL |
| V2 remote GitHub Actions | **Verified successful** for `02c82ae`: [run 36990489925](https://github.com/kaimouren/analysis_tool/actions/runs/36990489925), including new V2 eval step |
| Deliverable credential/private-path scan | **94 files; zero matches**, using common credential patterns plus configured-key matches and machine home-path patterns |

The browser's first load attempts timed out because the fixed test/debug connection resolved to another local application. The harness now allocates an independent debug port and verifies its exact target; the app was explicitly bound to loopback port 18517. The full browser smoke then passed. No other application was terminated. Screenshots are `docs/demo.png` and `docs/comparison.png`.

### Commands and scope

From the repository root with the existing Windows virtual environment:

```powershell
.venv-v1-1/Scripts/python -m pytest -q
.venv-v1-1/Scripts/python -m ruff check .
.venv-v1-1/Scripts/python -m pip check
.venv-v1-1/Scripts/python evals/comparison.py --output evals/comparison-results.json
.venv-v1-1/Scripts/python benchmarks/comparison.py --output benchmarks/comparison-results.json
# Clear provider configuration and history in this test shell.
$env:OPENAI_API_KEY=''
$env:OPENAI_BASE_URL=''
$env:QA_HISTORY_PATH=''
.venv-v1-1/Scripts/python -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 18517
# In another shell, set CHROME_PATH to your Chromium executable and:
$env:QA_BROWSER_PORT='18517'
.venv-v1-1/Scripts/python tests/browser_smoke.py
```

All four evaluation `run()` functions were also invoked together with assertions on every `passed` flag. Linux reused the isolated Debian interpreter and Linux packages described in the V1.2 section, running pytest, Ruff, pip consistency and all four evaluation suites. Source is on a Windows-mounted filesystem: this verifies Linux execution, not case-sensitive filesystem behavior or a Community Cloud image.

### Methods and edge cases

KS uses full finite empirical support; TVD uses full non-null category support unless high cardinality is explicitly suppressed. No sampling, random bins, p-values or significance claims. Centralized policy defaults: missing/rate changes 5/20 pp, rows 20/50%, KS and TVD .10/.25, uniqueness 10/30 pp, minimum 20 observations for distribution severity. Effective policy is embedded in results. See [methods](docs/V2_DRIFT.md) for formulas, zero denominators, datetime cadence rules and the 1e-12 boundary tolerance.

Tests cover empty/one-row/disjoint schemas, nullable types, missingness both directions, constant distributions, non-finite values, huge integers, supported extreme floats and safely rejected magnitudes, malformed dates, high cardinality, category ordering, unseen categories/zero probabilities, duplicate headers, row permutations and concurrent warning restoration. Local history tests cover save/reload, pruning/idempotence, preserved corruption recovery, wrong JSON types and locked-database safety. Mocked UI tests verify generated labels and rejected-output fallback. See [red-team findings](docs/V2_RED_TEAM.md).

### V2 resource snapshot

Windows/Python 3.11.3, pandas 2.3.3, NumPy 2.4.6, eight logical CPUs. Two four-column frames per case; fresh process per size; input construction excluded; sampled RSS every 5ms includes retained inputs and imports. Core only: no CSV parsing, Streamlit, history, LLM or concurrent-user cost.

| Rows per input | Seconds | Sampled peak RSS |
|---|---:|---:|
| 1,000 | 0.0788 | 77.48 MiB |
| 10,000 | 0.4855 | 86.20 MiB |
| 100,000 | 4.7726 | 167.70 MiB |

These are single local observations, not latency percentiles or hosted capacity. Both uploads/frames can coexist with a retained single-dataset session. Per-input limits and serialized analysis do not bound total host memory.

Remaining uncertainty: uncalibrated severity, overlapping findings, lossy CSV inference, skipped/tiny distributions, approximate float64 moments, no business calendar or causal inference, lexical-only explanation guards, local history without tenant isolation, no persistent baseline snapshot, no verified public V2 deployment. Earlier sections below retain historical V1 evidence and remote run links.

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
