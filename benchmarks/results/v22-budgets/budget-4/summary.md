# Agent behavior benchmark

Benchmark `91743dcff6c64c11bcd119612c83ed10`; complete: **True**.

Model `gpt-4o-mini`, provider `api.openai.com`, prompt `planner-v2.1`.

Configuration-specific observations; not universal agent accuracy.

## Overall metrics

| Metric | Mean / rate | Min–max | Stddev | N |
|---|---:|---|---:|---:|
| tool_relevance | 0.2 | 0.0 – 1.0 | 0.4 | 5 |
| tool_selection_accuracy | 0.9333333333333333 | 0.6666666666666666 – 1.0 | 0.13333333333333336 | 5 |
| tool_argument_validity | 1.0 | 1.0 – 1.0 | 0.0 | 5 |
| required_step_coverage | 0.8333333333333334 | 0.0 – 1.0 | 0.37267799624996495 | 6 |
| evidence_coverage | 0.08333333333333333 | 0.0 – 0.5 | 0.18633899812498247 | 6 |
| answer_coverage | 0.08333333333333333 | 0.0 – 0.5 | 0.18633899812498247 | 6 |
| evidence_grounding | 1.0 | 1.0 – 1.0 | 0.0 | 5 |
| unsupported_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 5 |
| contradicted_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 5 |
| recovery_rate | None | None – None | None | 0 |
| premature_stop | 0.8333333333333334 | 0 – 1 | 0.37267799624996495 | 6 |
| over_investigation | 0 | 0 – 0 | 0.0 | 6 |
| redundant_tool_rate | 0.0 | 0.0 – 0.0 | 0.0 | 5 |
| path_efficiency | 1 | 1 – 1 | 0.0 | 6 |
| stop_accuracy | 0 | 0 – 0 | 0.0 | 6 |
| completeness | 0.16666666666666666 | 0 – 1 | 0.37267799624996495 | 6 |
| tool_calls | 2.8333333333333335 | 1 – 4 | 0.8975274678557507 | 6 |
| successful_tool_calls | 2.8333333333333335 | 1 – 4 | 0.8975274678557507 | 6 |
| elapsed_seconds | 19.242333333333335 | 14.937 – 23.735 | 2.5706722639980555 | 6 |
| tool_seconds | 0.047199299947048225 | 0.022279399912804365 – 0.0874321002047509 | 0.02300316800341595 | 6 |
| model_seconds | 19.177215883353103 | 14.895779799902812 – 23.653199300169945 | 2.5604801033099633 | 6 |
| input_tokens | 14415.8 | 12214 – 18250 | 2696.3896899372685 | 5 |
| output_tokens | 245.4 | 220 – 306 | 32.71452276894774 | 5 |
| estimated_cost | None | None – None | None | 0 |
| run_success_rate | 0.0000 | — | — | — |
| scenario_success_rate | 0.0000 | — | — | — |

## Failure modes

| Failure | Runs |
|---|---:|
| incomplete_answer | 6 |
| missing_required_evidence | 6 |
| premature_stop | 5 |
| timeout | 1 |
| unexpected_status | 3 |
| wrong_tool | 1 |

## Scenario stability

| Scenario | Pass / runs | Stability | Path variance | Unstable |
|---|---:|---:|---:|---|
| device_country | 0/3 | 0.0 | 0.33333333333333337 | False |
| count_vs_aov | 0/3 | 0.0 | 0.33333333333333337 | False |

## Tool usage matrix

| Scenario | Schema | Time | Segment | Distribution | Quality | Profile | Group |
|---|---:|---:|---:|---:|---:|---:|---:|
| device_country | 3 | 3 | 3 | 0 | 1 | 0 | 0 |
| count_vs_aov | 3 | 2 | 2 | 0 | 0 | 0 | 0 |

## Representative failed trajectories

- **device_country**: schema → quality → time → segment; failures: incomplete_answer, missing_required_evidence, premature_stop, unexpected_status, wrong_tool; missing: conversion_rate_time, segment_device_conversion, segment_device_country_conversion.
- **count_vs_aov**: schema; failures: incomplete_answer, missing_required_evidence, timeout, unexpected_status; missing: revenue_count_time, revenue_mean_time, revenue_sum_time, segment_device_revenue.
