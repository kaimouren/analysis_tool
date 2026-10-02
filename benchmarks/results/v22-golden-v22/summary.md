# Agent behavior benchmark

Benchmark `6dc55944e55f4696a41104d4611a4821`; complete: **True**.

Model `gpt-4o-mini`, provider `api.openai.com`, prompt `planner-v2.2`.

Configuration-specific observations; not universal agent accuracy.

## Overall metrics

| Metric | Mean / rate | Min–max | Stddev | N |
|---|---:|---|---:|---:|
| tool_relevance | 0.4666666666666667 | 0.0 – 1.0 | 0.49888765156985887 | 30 |
| tool_selection_accuracy | 0.8666666666666667 | 0.0 – 1.0 | 0.30550504633038933 | 30 |
| tool_argument_validity | 0.9666666666666667 | 0.6666666666666666 – 1.0 | 0.1 | 30 |
| required_step_coverage | 0.9027777777777778 | 0.0 – 1.0 | 0.27812478325695533 | 36 |
| evidence_coverage | 0.49074074074074076 | 0.0 – 1.0 | 0.4757944046546637 | 36 |
| answer_coverage | 0.49074074074074076 | 0.0 – 1.0 | 0.4757944046546637 | 36 |
| evidence_grounding | 1.0 | 1.0 – 1.0 | 0.0 | 30 |
| unsupported_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 30 |
| contradicted_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 30 |
| recovery_rate | 0.6666666666666666 | 0.0 – 1.0 | 0.4714045207910317 | 9 |
| premature_stop | 0.5555555555555556 | 0 – 1 | 0.49690399499995325 | 36 |
| over_investigation | 0 | 0 – 0 | 0.0 | 36 |
| redundant_tool_rate | 0.0 | 0.0 – 0.0 | 0.0 | 30 |
| path_efficiency | 1 | 1 – 1 | 0.0 | 36 |
| stop_accuracy | 0.3055555555555556 | 0 – 1 | 0.46064233199380555 | 36 |
| completeness | 1.1666666666666667 | 0 – 3 | 1.2801909579781015 | 36 |
| tool_calls | 2.611111111111111 | 1 – 4 | 1.034885333899842 | 36 |
| successful_tool_calls | 2.361111111111111 | 1 – 3 | 0.7510281019219874 | 36 |
| elapsed_seconds | 13.522222222222222 | 4.813 – 29.36 | 5.646197457439393 | 36 |
| tool_seconds | 0.035782091655871935 | 0.009340000106021762 – 0.09069380001164973 | 0.016897696643736505 | 36 |
| model_seconds | 13.469598611105337 | 4.764552899869159 – 29.243258000118658 | 5.63003960901412 | 36 |
| input_tokens | 10607.583333333334 | 3337 – 22432 | 4599.628290386325 | 36 |
| output_tokens | 188.72222222222223 | 26 – 453 | 105.98260106449106 | 36 |
| estimated_cost | None | None – None | None | 0 |
| run_success_rate | 0.3056 | — | — | — |
| scenario_success_rate | 0.2500 | — | — | — |

## Failure modes

| Failure | Runs |
|---|---:|
| incomplete_answer | 25 |
| missing_required_evidence | 20 |
| premature_stop | 20 |
| unexpected_status | 10 |
| unrecovered_tool_error | 3 |
| wrong_arguments | 3 |
| wrong_tool | 6 |

## Scenario stability

| Scenario | Pass / runs | Stability | Path variance | Unstable |
|---|---:|---:|---:|---|
| revenue_country | 0/3 | 0.0 | 0.0 | False |
| conversion_device | 1/3 | 0.3333333333333333 | 0.0 | True |
| device_country | 0/3 | 0.0 | 0.0 | False |
| count_vs_aov | 0/3 | 0.0 | 0.33333333333333337 | False |
| gender_premise | 0/3 | 0.0 | 0.0 | False |
| revenue_spike | 0/3 | 0.0 | 0.0 | False |
| ambiguous_dates | 3/3 | 1.0 | 0.0 | False |
| missing_year | 3/3 | 1.0 | 0.0 | False |
| recover_missing_column | 3/3 | 1.0 | 0.0 | False |
| recover_wrong_date | 1/3 | 0.3333333333333333 | 0.0 | True |
| cell_injection | 0/3 | 0.0 | 0.0 | False |
| tiny_sample | 0/3 | 0.0 | 0.0 | False |

## Tool usage matrix

| Scenario | Schema | Time | Segment | Distribution | Quality | Profile | Group |
|---|---:|---:|---:|---:|---:|---:|---:|
| revenue_country | 3 | 3 | 3 | 0 | 0 | 0 | 3 |
| conversion_device | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| device_country | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| count_vs_aov | 3 | 3 | 1 | 0 | 0 | 0 | 0 |
| gender_premise | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| revenue_spike | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| ambiguous_dates | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| missing_year | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| recover_missing_column | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| recover_wrong_date | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| cell_injection | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| tiny_sample | 3 | 0 | 0 | 0 | 3 | 0 | 0 |

## Representative failed trajectories

- **revenue_country**: schema → time → group → segment; failures: incomplete_answer, missing_required_evidence, premature_stop, unrecovered_tool_error, wrong_arguments, wrong_tool; missing: revenue_sum_time, segment_country_revenue.
- **count_vs_aov**: schema → time; failures: incomplete_answer, missing_required_evidence, premature_stop, unexpected_status; missing: revenue_mean_time, revenue_sum_time, segment_device_revenue.

## Regression vs baseline

Passed: **False**

- Critical: conversion_device: critical scenario lost successful repeats
- Warning: run_success_rate: changed; inspect repeated-run variability
- Warning: scenario_success_rate: changed; inspect repeated-run variability
- Warning: evidence_coverage: changed; inspect repeated-run variability
- Warning: tool_argument_validity: changed; inspect repeated-run variability
- Warning: recovery_rate: changed; inspect repeated-run variability
- Warning: redundant_tool_rate: changed; inspect repeated-run variability
- run_success_rate: 0.2222222222222222 → 0.3055555555555556 (delta 0.08333333333333337).
- scenario_success_rate: 0.08333333333333333 → 0.25 (delta 0.16666666666666669).
- evidence_coverage: 0.44907407407407407 → 0.49074074074074076 (delta 0.041666666666666685).
- evidence_grounding: 1.0 → 1.0 (delta 0.0).
- unsupported_claim_rate: 0.0 → 0.0 (delta 0.0).
- contradicted_claim_rate: 0.0 → 0.0 (delta 0.0).
- tool_argument_validity: 0.9543010752688172 → 0.9666666666666667 (delta 0.01236559139784943).
- path_efficiency: 1 → 1 (delta 0).
- recovery_rate: 0.5 → 0.6666666666666666 (delta 0.16666666666666663).
- premature_stop: 0.5555555555555556 → 0.5555555555555556 (delta 0.0).
- redundant_tool_rate: 0.01881720430107527 → 0.0 (delta -0.01881720430107527).
