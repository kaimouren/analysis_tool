# Agent behavior benchmark

Benchmark `c331e5a60c9b4a518c6d238344a41082-golden`; complete: **True**.

Model `gpt-4o-mini`, provider `api.openai.com`, prompt `planner-v2.1`.

Configuration-specific observations; not universal agent accuracy.

## Overall metrics

| Metric | Mean / rate | Min–max | Stddev | N |
|---|---:|---|---:|---:|
| tool_relevance | 0.3279569892473118 | 0.0 – 1.0 | 0.45295499505001174 | 31 |
| tool_selection_accuracy | 0.7338709677419355 | 0.0 – 1.0 | 0.37888924320900635 | 31 |
| tool_argument_validity | 0.9543010752688172 | 0.3333333333333333 – 1.0 | 0.14942948505040105 | 31 |
| required_step_coverage | 0.8194444444444444 | 0.0 – 1.0 | 0.3565416014720399 | 36 |
| evidence_coverage | 0.44907407407407407 | 0.0 – 1.0 | 0.4840343646043841 | 36 |
| answer_coverage | 0.44907407407407407 | 0.0 – 1.0 | 0.4840343646043841 | 36 |
| evidence_grounding | 1.0 | 1.0 – 1.0 | 0.0 | 28 |
| unsupported_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 28 |
| contradicted_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 28 |
| recovery_rate | 0.5 | 0.0 – 1.0 | 0.5 | 10 |
| premature_stop | 0.5555555555555556 | 0 – 1 | 0.49690399499995325 | 36 |
| over_investigation | 0 | 0 – 0 | 0.0 | 36 |
| redundant_tool_rate | 0.01881720430107527 | 0.0 – 0.3333333333333333 | 0.07243114830810472 | 31 |
| path_efficiency | 1 | 1 – 1 | 0.0 | 36 |
| stop_accuracy | 0.2222222222222222 | 0 – 1 | 0.41573970964154905 | 36 |
| completeness | 0.9166666666666666 | 0 – 3 | 1.1873172373979173 | 36 |
| tool_calls | 2.8055555555555554 | 1 – 5 | 1.0754700379225521 | 36 |
| successful_tool_calls | 2.361111111111111 | 1 – 4 | 0.917508031384097 | 36 |
| elapsed_seconds | 15.752527777777777 | 4.844 – 30.906 | 5.91946424230226 | 36 |
| tool_seconds | 0.04595271108620283 | 0.009449500124901533 – 0.1353786000981927 | 0.02707160375911933 | 36 |
| model_seconds | 15.686568791712894 | 4.781917299842462 – 30.851269999984652 | 5.9176682685368 | 36 |
| input_tokens | 12397.914285714285 | 3259 – 20555 | 4966.985394274759 | 35 |
| output_tokens | 205.77142857142857 | 26 – 528 | 110.63300610946231 | 35 |
| estimated_cost | None | None – None | None | 0 |
| run_success_rate | 0.2222 | — | — | — |
| scenario_success_rate | 0.0833 | — | — | — |

## Failure modes

| Failure | Runs |
|---|---:|
| incomplete_answer | 28 |
| missing_required_evidence | 21 |
| premature_stop | 20 |
| repeated_tool_call | 2 |
| timeout | 1 |
| unexpected_status | 16 |
| unrecovered_tool_error | 5 |
| wrong_arguments | 3 |
| wrong_tool | 12 |

## Scenario stability

| Scenario | Pass / runs | Stability | Path variance | Unstable |
|---|---:|---:|---:|---|
| revenue_country | 0/3 | 0.0 | 0.33333333333333337 | False |
| conversion_device | 2/3 | 0.6666666666666666 | 0.0 | True |
| device_country | 0/3 | 0.0 | 0.33333333333333337 | False |
| count_vs_aov | 0/3 | 0.0 | 0.33333333333333337 | False |
| gender_premise | 0/3 | 0.0 | 0.33333333333333337 | False |
| revenue_spike | 0/3 | 0.0 | 0.0 | False |
| ambiguous_dates | 3/3 | 1.0 | 0.0 | False |
| missing_year | 2/3 | 0.6666666666666666 | 0.33333333333333337 | True |
| recover_missing_column | 0/3 | 0.0 | 0.0 | False |
| recover_wrong_date | 1/3 | 0.3333333333333333 | 0.33333333333333337 | True |
| cell_injection | 0/3 | 0.0 | 0.0 | False |
| tiny_sample | 0/3 | 0.0 | 0.0 | False |

## Tool usage matrix

| Scenario | Schema | Time | Segment | Distribution | Quality | Profile | Group |
|---|---:|---:|---:|---:|---:|---:|---:|
| revenue_country | 3 | 3 | 0 | 0 | 0 | 0 | 5 |
| conversion_device | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| device_country | 3 | 3 | 3 | 0 | 2 | 0 | 0 |
| count_vs_aov | 3 | 3 | 3 | 0 | 1 | 0 | 0 |
| gender_premise | 3 | 1 | 0 | 0 | 2 | 0 | 2 |
| revenue_spike | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| ambiguous_dates | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| missing_year | 3 | 1 | 0 | 0 | 0 | 0 | 0 |
| recover_missing_column | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| recover_wrong_date | 3 | 3 | 2 | 0 | 1 | 0 | 0 |
| cell_injection | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| tiny_sample | 3 | 0 | 0 | 0 | 3 | 0 | 0 |

## Representative failed trajectories

- **revenue_country**: schema → time → group; failures: incomplete_answer, missing_required_evidence, timeout, unexpected_status, unrecovered_tool_error, wrong_tool; missing: segment_country_revenue.
- **revenue_country**: schema → time → group → group → group; failures: incomplete_answer, missing_required_evidence, premature_stop, repeated_tool_call, unexpected_status, unrecovered_tool_error, wrong_arguments, wrong_tool; missing: revenue_sum_time, segment_country_revenue.
