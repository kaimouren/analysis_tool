# Data QA Agent: evaluating the investigation rather than the answer alone

## Problem

V2.1's 36 scripted scenarios passed, and deterministic code authored all final
numeric claims. That established useful controller/tool guarantees, but did not
show whether a real model selected the right scope, gathered all requested
evidence, recovered from failure or stopped appropriately. An answer can be
entirely grounded and still fail the user's task.

V2.2 adds an independent behavior benchmark rather than adding product features.
Its purpose is to expose failures and make subsequent changes reviewable.

## System

The production agent uses a bounded controller, eight narrow deterministic tools,
strict argument validation and a cited evidence ledger. The model selects actions
and evidence; Python calculates and renders factual statements. A benchmark
invokes this same controller and SDK adapter, captures observable actions and
scores them offline. It has no unrestricted execution or LLM judge.

The existing production prompt remains `planner-v2.1`. An explicit candidate
`planner-v2.2` can be benchmarked without replacing that default. Tool descriptions,
prompt, validator and evaluator have recorded versions; prompt/schema hashes and
fixture fingerprints detect silent drift.

## Evaluation design

There are **36 synthetic tasks**, six each for direct, multi-step, unsupported-
premise, ambiguous, recovery and adversarial investigations. Each defines expected
evidence, argument/scope selectors, acceptable tool classes, status, prohibited
claims and call budget. Twelve form a golden subset. Six controlled recovery
tasks inject one declared failing call; subsequent choices are real model actions.
These probes are distinguished from spontaneous model mistakes.

The main benchmark ran **three repeats per task: 108 investigations**. A candidate
prompt ran the same 12 golden tasks three times (36 new investigations); the
baseline golden comparison reuses the corresponding full-suite runs. A separate
two-task, three-repeat experiment compared four- and eight-step/call budgets
(12 new investigations). Total new real investigations: **156**.

Configuration: requested `gpt-4o-mini`, `api.openai.com`, temperature omitted
(provider default), three concurrent workers, no SDK retries, 15-second request
timeout, normally eight steps/eight calls and three errors. Full capture began
**2026-10-02 10:49:32 UTC**. These are sequential experiments, not randomized paired
trials; provider variation and an unpinned model alias limit attribution.

Offline scoring replays each tool against the fixed fixture. It checks expected
scope and evidence separately from citation grounding, classifies final claims,
measures required steps, duplicate calls, premature stopping, recovery and
completeness, and compares normalized tool-class paths. Partial captures, altered
contracts, duplicate identities, non-finite metrics and stale schemas fail safely.

## Failure modes discovered

1. **Correct arithmetic on an incorrect period.** Some calls used the last second
   of a month as an exclusive endpoint rather than next-month midnight. The sample
   totals could still look correct, but the declared whole-month scope was not.
2. **Completed but incomplete.** In `count_vs_aov`, some runs returned completed
   after time/segment analysis without the required non-null count and mean
   comparisons. `device_country` sometimes omitted the joint subsegment analysis.
3. **Grounded yet wrong analysis class.** Some revenue tasks used whole-dataset
   `group_metric` instead of period contribution analysis. A sum by country does
   not explain a change between periods.
4. **Unstable clarification/recovery.** `missing_year` and `recover_wrong_date`
   had mixed outcomes across repeats. A safe partial answer does not automatically
   satisfy a scenario whose required evidence and final status are explicit.
5. **Aggregate improvement concealed a critical regression.** Candidate prompt
   success improved on golden tasks, while a critical conversion scenario lost a
   successful repeat. The regression gate rejected the candidate.
6. **Evaluator reproducibility bug.** Initial Linux replay rejected Windows
   fixture hashes because CSV hashing inherited operating-system line endings.
   Explicit canonical CRLF serialization fixed it without changing fixture data,
   expected results or the captured model actions.

Evaluator red-team tests additionally caught consistently forged answer/ledger
numbers, altered evidence with unchanged prose, missing/duplicate artifacts,
claimless runs falsely implying perfect grounding, timeout usage being treated
as complete, and ambiguous-task error limits being mistaken for clarification.

## Regression strategy

The saved real capture and pinned scored report form a baseline, including its
failures. Standard CI replays it with no provider access, alongside all V1/V2/V2.1
tests and the unchanged 36 scripted scenarios. A manual workflow runs new real
experiments and uploads synthetic artifacts. Saved replay detects evaluator/tool
drift; it does not substitute for generating new model decisions after a prompt
or provider change.

Safety gates reject unsupported/contradicted claims, altered tool evidence and
grounding below 99%. Any critical scenario losing successful repeats fails,
regardless of aggregate gains. Other adverse changes use a tolerance of the
larger of five percentage points or twice measured baseline standard error.
This is an operational threshold, not a statistical significance claim.

## Results

### Full baseline: planner-v2.1

| Measure | Observed result |
|---|---:|
| Successful runs | **21/108 — 19.44%** |
| Scenarios with all three runs successful | **4/36 — 11.11%** |
| Tool selection accuracy | 69.01% |
| Typed argument validity | 93.32% |
| Evidence grounding | 100%; all **255 material claims** mapped and independently supported |
| Required evidence coverage | 43.67% |
| Unsupported / contradicted claims | 0 / 0 |
| Recovery rate | 37.93% macro mean across 29 runs with errors |
| Premature stop rate | 54.63% |
| Redundant tool rate | 2.17% |
| Average calls / successful calls | 2.81 / 2.30 |
| Stop accuracy | 26.85% |
| Mean / median elapsed time | 15.61s / 15.13s |

Rates are macro means over runs with defined denominators. Empty-claim runs do
not inflate grounding. Estimated cost is unreported; failed-request token usage
can be unavailable. The metrics describe these exact contracts, not business
correctness in arbitrary data or universal model accuracy.

**Six unstable scenarios** had both passing and failing repeats:
`conversion_device` (2/3), `missingness_increase` (1/3), `duplicate_increase` (2/3),
`weak_names` (1/3), `missing_year` (2/3), `recover_wrong_date` (1/3).
Four scenarios passed 3/3, six were mixed, and 26 passed 0/3; mixed-run counts alone
would conceal those consistently failing tasks. The full per-scenario table is
retained, rather than reporting only an average.

Failure labels overlap: incomplete answer **79**, missing required evidence **64**,
premature stop **59**, unexpected status **54**, wrong tool **42**, unrecovered
tool error **18**, wrong arguments **17**, repeated call **7**, timeout **5**.
Zero unsupported claims did not imply a successful investigation.

### Prompt comparison on identical golden tasks

| Measure | planner-v2.1 | planner-v2.2 |
|---|---:|---:|
| Successful runs | 8/36 (22.22%) | 11/36 (30.56%) |
| All-repeat successful scenarios | 1/12 | 3/12 |
| Evidence coverage | 44.91% | 49.07% |
| Grounding | 100% | 100% |
| Critical `conversion_device` | **2/3** | **1/3** |

The aggregate success change was **+8.33 percentage points**, but the critical
scenario gate **failed**. The candidate remains opt-in; it was not promoted.
Three repeats do not establish that the prompt caused either the improvement or
the regression.

### Budget sensitivity

On `device_country` and `count_vs_aov`, three repeats each:

| Budget | Success | Premature stops | Mean calls | Mean elapsed |
|---|---:|---:|---:|---:|
| 4 steps / 4 calls | 0/6 | 5/6 | 2.83 | 19.24s |
| 8 steps / 8 calls | 0/6 | 6/6 | 3.00 | 19.51s |

More budget alone did not resolve missing analyses/scope errors in this small
sample. One four-step run timed out. This is not evidence that shorter budgets
are generally better.

## Lessons

Grounding, task coverage and process quality are separate properties. Code-owned
claims constrained fabrication, but could not make the planner choose the right
periods or satisfy every requested analysis. Independent replay prevents a forged
ledger from grading itself. Critical per-scenario checks prevent aggregate gains
from concealing regressions. Repeated runs expose failures that a single successful
demo hides.

The suite is synthetic and authored, its semantic selectors are deliberately
narrow, and accepted tool classes can penalize extra diagnostic paths. It does
not assess arbitrary prose, causal validity or all prompt-injection attacks.
Provider/model revisions, broad real-world datasets, larger repetition counts
and domain-owned contracts remain outside this portfolio release. V2.2 completes
the current feature scope; it does not start V3.

Artifacts: [full baseline](../benchmarks/baselines/investigation-v2.2/summary.md),
[candidate comparison](../benchmarks/results/v22-golden-v22/summary.md),
[budget comparison](../benchmarks/results/v22-budgets/comparison.json).
Definitions and commands: [AGENT_EVALUATION.md](AGENT_EVALUATION.md).
