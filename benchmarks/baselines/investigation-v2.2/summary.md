# Agent behavior benchmark

Benchmark `c331e5a60c9b4a518c6d238344a41082`; complete: **True**.

Model `gpt-4o-mini`, provider `api.openai.com`, prompt `planner-v2.1`.

Configuration-specific observations; not universal agent accuracy.

## Overall metrics

| Metric | Mean / rate | Min–max | Stddev | N |
|---|---:|---|---:|---:|
| tool_relevance | 0.2777777777777778 | 0.0 – 1.0 | 0.4129463540921807 | 96 |
| tool_selection_accuracy | 0.6901041666666666 | 0.0 – 1.0 | 0.3961444546678905 | 96 |
| tool_argument_validity | 0.9331597222222222 | 0.3333333333333333 – 1.0 | 0.15618970673130714 | 96 |
| required_step_coverage | 0.7962962962962963 | 0.0 – 1.0 | 0.3804192330402618 | 108 |
| evidence_coverage | 0.4367283950617284 | 0.0 – 1.0 | 0.4820425466343577 | 108 |
| answer_coverage | 0.4367283950617284 | 0.0 – 1.0 | 0.4820425466343577 | 108 |
| evidence_grounding | 1.0 | 1.0 – 1.0 | 0.0 | 88 |
| unsupported_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 88 |
| contradicted_claim_rate | 0.0 | 0.0 – 0.0 | 0.0 | 88 |
| recovery_rate | 0.3793103448275862 | 0.0 – 1.0 | 0.48521542343000995 | 29 |
| premature_stop | 0.5462962962962963 | 0 – 1 | 0.4978520392137061 | 108 |
| over_investigation | 0 | 0 – 0 | 0.0 | 108 |
| redundant_tool_rate | 0.021701388888888888 | 0.0 – 0.3333333333333333 | 0.0781780298416559 | 96 |
| path_efficiency | 1 | 1 – 1 | 0.0 | 108 |
| stop_accuracy | 0.26851851851851855 | 0 – 1 | 0.4431888127323822 | 108 |
| completeness | 1 | 0 – 3 | 1.2692955176439846 | 108 |
| tool_calls | 2.814814814814815 | 1 – 6 | 1.2483184849150162 | 108 |
| successful_tool_calls | 2.2962962962962963 | 1 – 4 | 0.8634476464351679 | 108 |
| elapsed_seconds | 15.609814814814815 | 4.844 – 30.906 | 6.073060326142472 | 108 |
| tool_seconds | 0.04895654723212054 | 0.009449500124901533 – 0.1353786000981927 | 0.023021095510289677 | 108 |
| model_seconds | 15.539700664845036 | 4.781917299842462 – 30.851269999984652 | 6.0633864128492 | 108 |
| input_tokens | 12107 | 3259 – 28037 | 5359.192353294631 | 103 |
| output_tokens | 201.02912621359224 | 26 – 537 | 106.94499596228157 | 103 |
| estimated_cost | None | None – None | None | 0 |
| run_success_rate | 0.1944 | — | — | — |
| scenario_success_rate | 0.1111 | — | — | — |

## Failure modes

| Failure | Runs |
|---|---:|
| incomplete_answer | 79 |
| missing_required_evidence | 64 |
| premature_stop | 59 |
| repeated_tool_call | 7 |
| timeout | 5 |
| unexpected_status | 54 |
| unrecovered_tool_error | 18 |
| wrong_arguments | 17 |
| wrong_tool | 42 |

## Scenario stability

| Scenario | Pass / runs | Stability | Path variance | Unstable |
|---|---:|---:|---:|---|
| revenue_country | 0/3 | 0.0 | 0.33333333333333337 | False |
| conversion_device | 2/3 | 0.6666666666666666 | 0.0 | True |
| missingness_increase | 1/3 | 0.3333333333333333 | 0.0 | True |
| category_disappears | 0/3 | 0.0 | 0.6666666666666667 | False |
| date_truncation | 0/3 | 0.0 | 0.33333333333333337 | False |
| duplicate_increase | 2/3 | 0.6666666666666666 | 0.0 | True |
| device_country | 0/3 | 0.0 | 0.33333333333333337 | False |
| count_vs_aov | 0/3 | 0.0 | 0.33333333333333337 | False |
| metric_quality | 0/3 | 0.0 | 0.6666666666666667 | False |
| quality_columns | 0/3 | 0.0 | 0.0 | False |
| test_mobile_candidate | 0/3 | 0.0 | 0.33333333333333337 | False |
| competing_segments | 0/3 | 0.0 | 0.0 | False |
| gender_premise | 0/3 | 0.0 | 0.33333333333333337 | False |
| mobile_improvement | 0/3 | 0.0 | 0.33333333333333337 | False |
| revenue_spike | 0/3 | 0.0 | 0.0 | False |
| stable_missingness | 0/3 | 0.0 | 0.0 | False |
| mobile_decline_false | 0/3 | 0.0 | 0.0 | False |
| nonexistent_category | 0/3 | 0.0 | 0.6666666666666667 | False |
| ambiguous_dates | 3/3 | 1.0 | 0.0 | False |
| ambiguous_revenue | 0/3 | 0.0 | 0.0 | False |
| ambiguous_rate | 3/3 | 1.0 | 0.0 | False |
| weak_names | 1/3 | 0.3333333333333333 | 0.6666666666666667 | True |
| missing_year | 2/3 | 0.6666666666666666 | 0.33333333333333337 | True |
| ambiguous_group | 3/3 | 1.0 | 0.0 | False |
| recover_missing_column | 0/3 | 0.0 | 0.0 | False |
| recover_wrong_aggregation | 0/3 | 0.0 | 0.33333333333333337 | False |
| recover_wrong_date | 1/3 | 0.3333333333333333 | 0.33333333333333337 | True |
| recover_too_many_groups | 0/3 | 0.0 | 0.6666666666666667 | False |
| recover_empty_period | 0/3 | 0.0 | 0.33333333333333337 | False |
| recover_unsupported_metric | 0/3 | 0.0 | 0.33333333333333337 | False |
| cell_injection | 0/3 | 0.0 | 0.0 | False |
| misleading_names | 3/3 | 1.0 | 0.0 | False |
| irrelevant_text | 0/3 | 0.0 | 0.0 | False |
| high_cardinality | 0/3 | 0.0 | 0.33333333333333337 | False |
| tiny_sample | 0/3 | 0.0 | 0.0 | False |
| all_null | 0/3 | 0.0 | 0.0 | False |

## Tool usage matrix

| Scenario | Schema | Time | Segment | Distribution | Quality | Profile | Group |
|---|---:|---:|---:|---:|---:|---:|---:|
| revenue_country | 3 | 3 | 0 | 0 | 0 | 0 | 5 |
| conversion_device | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| missingness_increase | 3 | 0 | 0 | 0 | 3 | 0 | 0 |
| category_disappears | 3 | 3 | 1 | 0 | 3 | 0 | 2 |
| date_truncation | 3 | 3 | 0 | 0 | 3 | 1 | 0 |
| duplicate_increase | 3 | 0 | 0 | 0 | 3 | 0 | 0 |
| device_country | 3 | 3 | 3 | 0 | 2 | 0 | 0 |
| count_vs_aov | 3 | 3 | 3 | 0 | 1 | 0 | 0 |
| metric_quality | 3 | 2 | 1 | 0 | 3 | 0 | 0 |
| quality_columns | 3 | 0 | 0 | 0 | 3 | 3 | 0 |
| test_mobile_candidate | 3 | 3 | 1 | 0 | 0 | 0 | 0 |
| competing_segments | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| gender_premise | 3 | 1 | 0 | 0 | 2 | 0 | 2 |
| mobile_improvement | 3 | 3 | 0 | 0 | 2 | 0 | 0 |
| revenue_spike | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| stable_missingness | 3 | 0 | 0 | 0 | 3 | 0 | 0 |
| mobile_decline_false | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| nonexistent_category | 3 | 5 | 0 | 0 | 1 | 0 | 1 |
| ambiguous_dates | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| ambiguous_revenue | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| ambiguous_rate | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| weak_names | 3 | 1 | 0 | 0 | 1 | 0 | 0 |
| missing_year | 3 | 1 | 0 | 0 | 0 | 0 | 0 |
| ambiguous_group | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| recover_missing_column | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| recover_wrong_aggregation | 3 | 3 | 2 | 0 | 6 | 0 | 0 |
| recover_wrong_date | 3 | 3 | 2 | 0 | 1 | 0 | 0 |
| recover_too_many_groups | 3 | 1 | 3 | 0 | 2 | 0 | 0 |
| recover_empty_period | 3 | 3 | 3 | 0 | 5 | 0 | 0 |
| recover_unsupported_metric | 3 | 3 | 1 | 0 | 3 | 0 | 0 |
| cell_injection | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| misleading_names | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| irrelevant_text | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| high_cardinality | 3 | 3 | 2 | 0 | 0 | 0 | 0 |
| tiny_sample | 3 | 0 | 0 | 0 | 3 | 0 | 0 |
| all_null | 3 | 0 | 0 | 0 | 3 | 0 | 0 |

## Representative failed trajectories

- **revenue_country**: schema → time → group; failures: incomplete_answer, missing_required_evidence, timeout, unexpected_status, unrecovered_tool_error, wrong_tool; missing: segment_country_revenue.
- **revenue_country**: schema → time → group → group → group; failures: incomplete_answer, missing_required_evidence, premature_stop, repeated_tool_call, unexpected_status, unrecovered_tool_error, wrong_arguments, wrong_tool; missing: revenue_sum_time, segment_country_revenue.
