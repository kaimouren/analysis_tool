# V1 audit

Baseline: `38d4aef`. Audit completed before architectural changes. The tracked repository, source, tests, README, validation history, settings, sample generator, and CI were inspected. Baseline `pytest -q`: **31 passed**. The local Streamlit server was reachable and the existing AppTest suite exercised its sample and explorer behavior.

## Architecture and strengths

`app.py` is the entrypoint. `qa_core.py` contains loader, profiler, checks, severity and score functions; `config.py` handles environment/secrets and the 10 MiB guard; `llm.py` provides authored guidance and validated optional prose; `report.py`/`presentation.py` render facts and interpretations. Tests use small in-memory fixtures and the planted 500-row CSV. Reports and UI remain useful without a provider. Score policy 1.0 is explicit, reproducible, and separated from the LLM. Existing privacy tests protect aliases and aggregate-only payloads. The small layout is appropriate; creating nine packages would add navigation without improving boundaries.

## Risks and selected responses

| Area | Baseline evidence / gap | V1 response |
|---|---|---|
| Reliability / ingestion | pandas silently renames duplicate CSV headers; NUL-containing input is accepted; only byte size is bounded | Inspect headers before pandas; reject duplicate/blank headers and binary controls; constrain columns, rows, cells and decoded frame memory; explicit actionable exceptions |
| Malformed input | Some expected errors share a generic ValueError; file extension is UI-only | Dedicated safe ingestion exception; filename validation; exercise malformed, unsupported and Unicode inputs |
| Checks | Whitespace/case variants are not findings; some constant/ID findings have empty evidence | Add conservative, non-scoring text-format warnings; populate evidence for every finding |
| Severity/config | Percentage thresholds centralized, other heuristic constants remain inline | Frozen typed policy settings with validated notebook overrides; persist effective policy with results |
| Data models | Nested dictionaries are convenient but finding fields have no enforced shape | Frozen finding and analysis-metadata dataclasses at construction boundaries; keep compatible JSON dictionaries for users |
| Security | Sidebar alternate endpoint plus own key permits arbitrary server egress | Server-controlled exact endpoint allowlist; no raw exception messages or uploaded content in logs |
| Privacy | No dedicated threat model; filenames/column names can be interpreted as Markdown by UI | Privacy document; render data labels as text; escape report content; no automatic file persistence |
| LLM | Prompt does not explicitly distinguish possible root causes from established causes; failures have no safe diagnostic code | Explicit root-cause constraint; categorized content-free failure events; preserve schema and issue-order validation |
| Observability | No analysis timings or structured events | Low-volume JSON events for ingestion, analysis, checks, report and provider lifecycle; whitelist numeric and controlled fields |
| Performance | No measured scale evidence; integer-sequence hint sorts even noninteger columns | Benchmark before claims; only sort eligible integer candidates; bound inputs, no distributed engine |
| Reporting | No timestamp/application metadata; recommendations only for top five | Separate nondeterministic run metadata from deterministic profile; standalone methodology, evidence and guidance for all findings |
| UX | No finding-count summary; detailed evidence can be dense | Compact severity counts; keep top-five flow and expandable details |
| Evaluation | Good tests but no independent multi-fixture eval oracle | Eight synthetic CSV cases, declared expected finding identities/severities/scores; runner fails on unexpected or missed findings |
| Testing | Threshold neighbor tests incomplete; no strict-header/binary/log-redaction cases | Boundary, ingestion, score-scenario, privacy and integration tests; lightweight lint |
| Deployment | Prior runs reused an environment; no env example; no clean-install validation | Fresh virtual environment install and tests; env example; CI eval/lint; keep Streamlit deployment without Docker |

## Scope and technical debt

V1 answers which **implemented structural/statistical signals** exist, how the rules rate them, and what to investigate next. It does not establish business correctness. Duplicate entity IDs, logical date ranges, business-invalid numeric values, fairness, leakage, contracts, monitoring, authentication and databases remain outside scope.

The score is an uncalibrated policy index. Preserve its weights and sample score, rather than inventing evidence for new weights. Text-format warnings will be explicitly advisory and excluded from scoring to avoid correlated penalty inflation. Confidence will distinguish exact observations from uncertain semantic interpretations, not claim a numeric posterior.

Remaining debt accepted for V1: flat dictionaries at the public notebook boundary, in-memory CSV processing, broad compatibility ranges, heuristic date/ID inference, lexical severity ties, no concurrency load test, and model prose that can still be wrong. Benchmarks must report hardware, dimensions, measurement method, and measured limitations; no enterprise-scale claim is justified.

Completion evidence will be recorded in `VALIDATION.md`, `evals/results.json`, and `benchmarks/results.json`. The audit describes the baseline; it is not a claim that all work above was already implemented.

## Completion reference

The selected V1 changes are now implemented and verified. `VALIDATION.md` records the clean-environment 56-test result, eight-case eval, measured benchmarks, real browser upload/download run and scoped secret scan. The accepted limitations above remain; no enterprise-scale or real-world accuracy claim was added.
