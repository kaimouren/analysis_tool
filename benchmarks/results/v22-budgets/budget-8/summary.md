# Agent behavior benchmark

Benchmark `d8d71c1d3a1c49f693aac8471f3bd1d7`; complete: **True**.

Model `gpt-4o-mini`, provider `api.openai.com`, prompt `planner-v2.1`.

Configuration-specific observations; not universal agent accuracy.

## Overall metrics

| Metric | Mean / rate | Min–max | Stddev | N |
|---|---:|---|---:|---:|
| tool_relevance | 0.16666666666666666 | 0.0 – 1.0 | 0.37267799624996495 | 6 |
| tool_selection_accuracy | 1.0 | 1.0 – 1.0 | 0.0 | 6 |
| tool_argument_validity | 1.0 | 1.0 – 1.0 | 0.0 | 6 |
| required_step_coverage | 1.0 | 1.0 – 1.0 | 0.0 | 6 |
| evidence_coverage | 0.1111111111111111 | 0.0 – 0.6666666666666666 | 0.24845199749997662 | 6 |
| answer_coverage | 0.1111111111111111 | 0.0 – 0.6666666666666666 | 0.24845199749997662 | 6 |
| evidence_grounding | 1.0 | 1.0 – 1.0 | 0.0 | 6 |
| unsupported_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 6 |
| contradicted_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 6 |
| recovery_rate | None | None – None | None | 0 |
| premature_stop | 1 | 1 – 1 | 0.0 | 6 |
| over_investigation | 0 | 0 – 0 | 0.0 | 6 |
| redundant_tool_rate | 0.0 | 0.0 – 0.0 | 0.0 | 6 |
| path_efficiency | 1 | 1 – 1 | 0.0 | 6 |
| stop_accuracy | 0 | 0 – 0 | 0.0 | 6 |
| completeness | 0.16666666666666666 | 0 – 1 | 0.37267799624996495 | 6 |
| tool_calls | 3 | 3 – 3 | 0.0 | 6 |
| successful_tool_calls | 3 | 3 – 3 | 0.0 | 6 |
| elapsed_seconds | 19.510333333333335 | 15.078 – 25.532 | 3.483592526241967 | 6 |
| tool_seconds | 0.05977225004850576 | 0.03482960001565516 – 0.09717369987629354 | 0.020640656103534615 | 6 |
| model_seconds | 19.394252616679296 | 14.986034899950027 – 25.381556400097907 | 3.473563844365627 | 6 |
| input_tokens | 16685 | 12382 – 22933 | 3600.839022598298 | 6 |
| output_tokens | 297.6666666666667 | 258 – 344 | 28.813577046632414 | 6 |
| estimated_cost | None | None – None | None | 0 |
| run_success_rate | 0.0000 | — | — | — |
| scenario_success_rate | 0.0000 | — | — | — |

## Failure modes

| Failure | Runs |
|---|---:|
| incomplete_answer | 6 |
| missing_required_evidence | 6 |
| premature_stop | 6 |
| unexpected_status | 3 |

## Scenario stability

| Scenario | Pass / runs | Stability | Path variance | Unstable |
|---|---:|---:|---:|---|
| device_country | 0/3 | 0.0 | 0.0 | False |
| count_vs_aov | 0/3 | 0.0 | 0.0 | False |

## Tool usage matrix

| Scenario | Schema | Time | Segment | Distribution | Quality | Profile | Group |
|---|---:|---:|---:|---:|---:|---:|---:|
| device_country | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| count_vs_aov | 3 | 3 | 3 | 0 | 0 | 0 | 0 |

## Representative failed trajectories

- **device_country**: schema → time → segment; failures: incomplete_answer, missing_required_evidence, premature_stop; missing: segment_device_country_conversion.
- **device_country**: schema → time → segment; failures: incomplete_answer, missing_required_evidence, premature_stop, unexpected_status; missing: conversion_rate_time, segment_device_conversion, segment_device_country_conversion.
