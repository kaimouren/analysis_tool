# Data QA Agent: portfolio summary

## Project

Data QA Agent is a Python and Streamlit project that grew from deterministic CSV quality checks into a bounded data investigation agent, with real-model trajectory evaluation and regression CI. Users can inspect one dataset, compare it with a baseline, or ask an investigation question. Python computes the evidence; the model selects registered analyses and evidence references. The project is complete through V2.2. Its strongest result is a measured reliability gap, together with infrastructure that makes that gap inspectable and prevents aggregate improvements from hiding critical regressions.

## Problem

An agent can return a plausible, fully cited answer and still fail the task. It might compare the wrong periods, omit a requested analysis, stop before collecting enough evidence, or fail to recover from an invalid tool call. Final-answer provenance alone does not measure these behaviors. A successful scripted demo also says little about how consistently a real model will choose the right actions.

The engineering problem was to separate arithmetic correctness, evidence provenance, question coverage, and planning behavior. Each needs an explicit contract and its own checks. Without that separation, a single reassuring score can conceal important failures.

## System

The application provides three modes: single-dataset QA, baseline comparison, and natural-language investigation. QA measures missingness, duplicates, types, outliers, and other structural signals. Comparison measures schema and distribution changes, including missingness, cardinality, and datetime coverage. These modes remain usable without model credentials.

Investigation uses eight narrow tools for schema inspection, summaries, column profiles, quality checks, period comparisons, segment contributions, group metrics, and distribution comparisons. Strict Pydantic schemas validate actions and arguments. The controller enforces default limits of eight planning steps, eight attempted tool calls, three errors, and a soft 120-second deadline. The bootstrap schema call consumes tool budget. The model has no unrestricted Python, SQL, shell, or external-connector capability.

The planner returns actions and evidence IDs, not accepted final prose. Deterministic code authors and renders factual claims from the evidence ledger. The UI exposes arguments, errors, citations, status, and limitations. This makes the interpreted analytical scope reviewable, while avoiding any display or storage of hidden model reasoning. It still cannot guarantee that the selected scope faithfully represents every natural-language request.

## Reliability work

Hardening progressed through input validation, scoring stress tests, parser and concurrency checks, drift analysis, controller red-team tests, and independent trajectory evaluation. Tests exercise malformed artifacts, forged evidence, unsupported premises, repeated calls, incorrect scopes, partial captures, and ambiguous completion. Recorded validation includes 272 passing tests on both Windows and Linux.

Evaluation has two distinct layers. The first uses scripted planners with real tools and the real controller: 36 investigation regression scenarios passed. The second records repeated real-model decisions on 36 manually designed synthetic tasks, including 12 golden tasks. Each scenario declares evidence requirements, acceptable tool classes, scope, status, and budgets. Six recovery probes inject a disclosed failing call before model decisions; forced calls are excluded from model-selection and argument-validity denominators.

Offline evaluation recomputes tools against fixed fixtures instead of trusting saved claims. It checks evidence linkage and values separately from coverage and completeness. Artifact contracts preserve configuration, prompt/schema versions, fixture fingerprints, and run identity. Standard GitHub Actions CI replays saved trajectories without paid API access; a separate optional manual workflow can capture new model runs.

## Most important result

The main benchmark used OpenAI `gpt-4o-mini`, `planner-v2.1`, three repeats per scenario, and eight-step/eight-call limits. Capture began on October 2, 2026. Only **21/108 runs succeeded (19.44%)**, despite the **36/36 scripted regressions** passing. Only four of the 36 real-model scenarios passed every repeat.

Recorded final claims had **100% evidence grounding and 0% unsupported claims**: 255 material claims across 88 claim-bearing runs. That did not mean the investigations were complete. Evidence coverage was 43.67%, and the premature-stop rate was 54.63%. Overlapping failure labels included 79 incomplete answers, 64 missing-evidence failures, and 42 wrong-tool failures. The main failures were missing analyses and poor stopping or recovery, rather than fabricated numbers.

V2.2 recorded **156 new real investigations**: 108 baseline runs, 36 candidate-prompt runs, and 12 budget-probe runs. The golden baseline reused full-suite captures. These are configuration-specific observations, not universal model accuracy or evidence of real-world population reliability.

## Regression-gate example

The candidate `planner-v2.2` produced 11/36 successful golden runs, compared with 8/36 for the existing prompt. However, the critical `conversion_device` scenario fell from 2/3 successful repeats to 1/3. The gate rejected the candidate, and the production default remains `planner-v2.1`.

The gate also rejects unsupported or contradicted claims, altered tool evidence, and grounding below its floor. Other adverse metric changes use documented operational tolerances. Three repeats do not establish statistical significance or a causal prompt effect. The point of the experiment is that aggregate gains must remain subordinate to explicitly protected behaviors.

## Technical skills demonstrated

- Python data engineering: reusable deterministic profiling, drift metrics, aggregation, and numerical boundary handling.
- Agent architecture: structured actions, a registered tool boundary, bounded orchestration, explicit errors, and evidence-based completion.
- Evaluation engineering: scenario contracts, repeated captures, independent replay, failure taxonomy, and per-scenario regression protection.
- Release engineering: cross-platform tests, dependency/lint checks, offline CI, reproducible artifacts, and documented deployment limits.

## Limitations

The benchmark is synthetic, manually authored, and small. Strict scope selectors and accepted analysis classes may penalize alternative reasonable paths. Results depend on model, provider, prompt, and runtime configuration; the requested model alias is not an immutable revision. Structured claim validation is not a universal semantic truth detector. Segment contributions identify observed arithmetic associations, not causes.

Public Streamlit deployment remains unverified; no public demo URL is claimed. A public demonstration should omit shared provider credentials and leave local history disabled. There are no per-user quotas or tenant-isolation guarantees. Estimated cost is unavailable, so no cost-performance claim is made. Frozen replay checks tools and evaluation behavior; it cannot substitute for fresh model decisions after a planner change.

Sources: [evaluation methodology](AGENT_EVALUATION.md), [case study](AGENT_RELIABILITY_CASE_STUDY.md), [validation](../VALIDATION.md), and [deployment instructions](DEPLOYMENT.md).
