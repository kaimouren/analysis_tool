# Adversarial review and hardening decisions

Baseline: commit `6c22f9f`, inspected before changes. All 17 existing tests passed. Ratings below describe that baseline, not the completed improvements. The source, tests, docs, settings, CI, sample generator, and current UI paths were inspected.

## Initial assessment

The architecture separates CSV loading, profiling, detection, and scoring into functions in `qa_core.py`; optional structured explanation lives in `llm.py`, Markdown formatting in `report.py`, configuration in `config.py`, and presentation in `app.py`. The deterministic boundary is enforced: model fields cannot replace calculated results. The frontend could be replaced without rewriting the core.

Strong choices: no dataset mutation, offline usefulness, capped reproducible penalties, exact issue evidence, provider timeouts, and anonymous aggregate-only LLM payloads. Weak choices: uncalibrated weights without a rationale, alphabetical ties marketed as priorities, generic explanation templates, and a score that visually outweighs scope caveats. The README acknowledges several limitations better than the UI does.

Reproduced before edits: all-null and header-only DataFrames crash Plotly's empty categorical chart; a one-row numeric dataset scores 82 with constant and possible-ID findings; 99 clean numeric columns plus one entirely missing column score 99.7; a deliberately right-skewed numeric series triggers high IQR prevalence and scores 89.5. These are evidence for clearer interpretation and edge handling, not evidence for tuning weights until examples look better.

Interview questions needing better answers: Why these weights? Is the score calibrated? Can a high score hide an unusable feature? Does a parsed date mean the intended date? Why call a unique product name an ID? What does the model add that deterministic guidance cannot?

## Questions 1–30: implementation assessment

| # | Question | Baseline rating | Actual behavior and decision |
|---|---|---|---|
| 1 | Why deterministic + LLM? | STRONG | `explain_profile` receives aggregates; Pydantic has no result replacement fields. UI/report use the original profile. Prose truthfulness is not guaranteed. |
| 2 | Can the LLM change issues/severity/rank/score/stats? | STRONG | No merge into computed facts; issue IDs and order are checked. Keep numeric fields out of generated text. |
| 3 | Is the core reusable? | STRONG | No Streamlit or network import in `qa_core.py`; direct DataFrame API is tested. CSV byte limit applies to the loader, not notebook DataFrames. |
| 4 | Are boundaries clean? | PARTIAL | Core functions separate responsibilities, but authored guidance and report formatting depend on the API module. Keep this small dependency; centralize shared issue presentation instead of duplicating UI/report language. |
| 5 | Useful without the LLM? | STRONG | Metrics, flags, charts, authored guidance, and export work on the sample without a key. Empty-chart defects are a separate reliability issue. |
| 6 | What does the score mean? | PARTIAL | It is 100 minus weighted generic findings, not readiness. Say this next to the score, not only in README. |
| 7 | False precision / bands? | PARTIAL | Two decimal places reflect arithmetic, not measured certainty. Add a severity-derived review status; reject score-derived Healthy bands because a 99.7 score can coexist with a critical finding. |
| 8 | Why these weights/caps? | WEAK | Formula is reproducible but weights are uncalibrated policy choices. Document the purpose and relative importance of each cap; do not invent scientific justification. |
| 9 | Double penalties? | PARTIAL | Constant and near-constant are exclusive; missingness, concentration, duplication, IDs, and IQR flags can overlap. Explicitly disclose additive, correlated penalties rather than claiming independent defects. |
| 10 | One bad column dominates? | STRONG | Column and cell denominators prevent this: the 99-clean/one-null probe incurs only 0.3 points. Conversely, averaging can hide that critical feature; surface worst-column missingness and review status. |
| 11 | High score yet unusable for ML? | OUT OF SCOPE | No target, task, split, or domain contract exists. Clearly exclude leakage, contamination, imbalance, bias, impossible values, and readiness guarantees. |
| 12 | Overall vs column missingness? | PARTIAL | Per-column values exist in the explorer; one missing column can disappear in the aggregate. Add an ordered column-missingness overview and worst-column metric. |
| 13 | Missingness cutoffs defensible? | PARTIAL | 5/20/50% thresholds are documented, but not justified as triage conventions. Explain heuristic thresholds and expose the actual severity rule. |
| 14 | Remediation simplistic? | STRONG | Authored guidance asks about the missingness mechanism and training-only imputation; no automatic dropping or cleaning. Preserve this caution. |
| 15 | Why IQR? | PARTIAL | Fences and denominators are exact; rationale and failure modes are thin. Explain robustness to extremes, skew, small samples, discreteness, and zero-IQR behavior. |
| 16 | Overconfident outlier label? | PARTIAL | Guidance allows valid extremes, but headings simply say Outliers. Use IQR-flagged values in UI/report while keeping stable internal type identifiers. |
| 17 | Skew causes many flags? | WEAK | The skewed probe triggers high prevalence with no local caveat. Add a chart/issue caveat; do not add a distribution classifier. |
| 18 | Outliers scaled by prevalence? | STRONG | Percentages use finite values and penalties use pooled numeric prevalence; raw counts do not determine severity. Document dilution by other numeric columns and the 1% scoring gate. |
| 19 | Why 95% near-constant? | PARTIAL | Exact rule exists, but the cutoff is arbitrary. Document a practical concentration screen, not proof that rare values lack signal. |
| 20 | Constant vs near-constant? | STRONG | Mutually exclusive flags, high vs medium severity, and different remediation. Keep. |
| 21 | High cardinality confused with IDs? | PARTIAL | Any short unique string or integer-like column can trigger, including dates/products. Relabel as high cardinality / possible ID and show name/sequence evidence without claiming a true identifier. |
| 22 | Multiple ID signals? | PARTIAL | Already uses ratio, dtype/integer-likeness, and median length, but no semantic hints. Add small, observable name/sequence evidence; keep the broad compatibility flag and small penalty unchanged. |
| 23 | Does UI express uncertainty? | PARTIAL | Possible Id heading is tentative; fallback says ID-like uniqueness. Clarify that uniqueness does not establish role, leakage, or exclusion. |
| 24 | Mixed string edge cases? | PARTIAL | Strict numeric/date parsers split numeric tokens from unknown/currency/percentage strings; pandas loading first turns N/A into null and can erase leading zeros. Test these separately and expose parser counts. |
| 25 | Identifier strings called numeric? | WEAK | All numeric-looking strings are labeled numeric, even zero-padded codes supplied as strings. Use numeric-like text / identifier-like text labels and a zero-padding count; do not reinterpret loaded numeric columns or change source values. |
| 26 | Mixed detection explainable? | WEAK | Only a minority percentage is displayed. Add numeric/date/neither counts, denominator, and limited local examples; keep raw examples out of the LLM payload. |
| 27 | Meaning of date parseability? | PARTIAL | 95% labels datetime; 80% is mixed, not datetime. Rename text inference datetime-like and show parser-success caveat. No automatic conversion. |
| 28 | Ambiguous dates? | WEAK | Month-first parsing counts 01/02/2024 as success; two-digit years are excluded. Explicitly disclose ambiguity and preserve the raw date strings. |
| 29 | Are duplicates inherently bad? | PARTIAL | Template already permits legitimate repeats; headline is unqualified. Use potential duplicate rows and specify exact rows after the first, not entity duplicates. |
| 30 | Duplicate identifiers? | OUT OF SCOPE | No schema establishes a primary key, so repeated IDs may be valid longitudinal observations. Do not add an ID-duplicate defect without a declared contract. |

## Questions 31–40: interview-level disposition

A = code; B = UI; C = documentation; D = deliberately out of scope.

| # | Question | Baseline rating | Disposition and concrete answer |
|---|---|---|---|
| 31 | Actual promise? | PARTIAL | B/C: surface common structural and statistical signals for a first review; never promise every modeling problem. |
| 32 | Beyond pandas.describe? | PARTIAL | C: explicit rules, stable triage, penalty audit, actionable conditional guidance, and export form a review workflow; describe supplies summaries, not this policy. |
| 33 | Beyond ydata-profiling? | PARTIAL | C: a smaller opinionated triage workflow, not a superior profiler or unique feature inventory. YData also offers reports and alerts. |
| 34 | Beyond Great Expectations? | PARTIAL | C/D: exploratory screening without a declared contract; GX validates expectations and suites. Production contract validation stays out of scope. |
| 35 | Discover or prove validity? | PARTIAL | B/C: discover signals; a clean result only means these rules did not fire. |
| 36 | Does score imply certification? | PARTIAL | B/C: label heuristic and describe unmeasured risks directly in results and reports. |
| 37 | Why triggered? | PARTIAL | A/B: existing stat/value/detection threshold are present; add a deterministic severity-rule field so detection and assigned severity are independently explainable. |
| 38 | Fact vs interpretation? | PARTIAL | A/B: separate observed fact, detection rule, severity rule, and labeled authored or generated interpretation in UI and report. |
| 39 | Why this score? | PARTIAL | B/C: breakdown exists; attach cap/rationale and clarify overlapping penalties and dilution. |
| 40 | Trust as first-pass check? | PARTIAL | A/B/C: fix reproduced chart crashes, disclose weak semantics and uncalibrated score, and test both findings and absence of findings. No claim of universal correctness. |

Comparison sources: [YData profiling quickstart](https://docs.profiling.ydata.ai/4.14/getting-started/quickstart/), [YData configuration](https://docs.profiling.ydata.ai/latest/advanced_settings/available_settings/), and [Great Expectations validation](https://docs.greatexpectations.io/docs/core/run_validations/). These products overlap with this app; the distinction is workflow and scope, not claimed superiority.

## Questions 41–50: product maturity

| # | Question | Baseline rating | Actual behavior and decision |
|---|---|---|---|
| 41 | Empty state scope? | PARTIAL | Upload/sample are discoverable, exclusions absent. Add one concise scope sentence. |
| 42 | Results hierarchy? | PARTIAL | Metrics and top five lead, but a large score can overshadow severity. Put severity-derived review status next to it. |
| 43 | Consistent severity? | PARTIAL | Cards use four colors, explorer uses warning styling for everything. Use the same badge mapping for issue details, including low flags. |
| 44 | Too many warnings? | PARTIAL | Top five and all-issue expander limit noise; the selected column dumps warning boxes. Use compact details and state that within-severity ordering is lexical, not business priority. |
| 45 | Specific explanation? | PARTIAL | Templates are generic but have adjacent numbers. Add a deterministic observation sentence with count/denominator; keep numeric claims outside LLM prose. |
| 46 | Report retains evidence? | STRONG | Score, penalties, severity, stats, and fixes survive export. Extend with severity rules and context rather than replacing evidence. |
| 47 | Report labels heuristics? | PARTIAL | Generic score caveat exists, but unqualified headings remain. Add scope, review status, policy version, and uncertainty-aware names. |
| 48 | Edge datasets graceful? | WEAK | Core handles empty and null data; frontend fails on both. Tiny data is technically accepted but over-interpretable. Fix chart guards and warn about limited evidence. |
| 49 | Empty charts / broken states? | WEAK | Reproduced Plotly ValueError on empty x/y arrays, hiding export. Render a no-observations message and keep report available. |
| 50 | Understandable in 60 seconds? | PARTIAL | Layout is short but scope and rule meaning are buried. Improve those labels; do not claim a measured usability result without user testing. |

## Selected changes

| Finding | Current status | User impact | Proposed change | Priority |
|---|---|---|---|---|
| Null/header-only chart crash | WEAK | Results and export fail | Guard absent values; regression tests through Streamlit | P0 |
| Aggregate score can conceal severe local findings | PARTIAL | High score mistaken for readiness | Heuristic label, severity-derived review status, worst-column missingness; retain formula | P0 |
| Severity unexplained | PARTIAL | Cannot audit why a badge is high | Shared deterministic rule metadata and fact/rule/interpretation presentation | P1 |
| Numeric/date/ID semantics overstate knowledge | WEAK | Valid strings may be treated as invalid or numeric | Parsing evidence, cautious labels, bounded local examples and name/sequence hints | P1 |
| Arbitrary weights and correlated flags under-explained | WEAK | Interview and trust gap | Per-cap rationale, overlap/dilution examples, explicit lack of calibration | P1 |
| Small samples and skew lack context | PARTIAL | Literal flags overgeneralized | Heuristic small-sample notice, IQR/date limitations, adversarial tests | P1 |
| Healthy score bands | PARTIAL | Reinforces false certainty | Reject; use highest detected severity rather than new score thresholds | OUT |
| Retuning weights without outcomes | WEAK | Cosmetic scores lack evidence | Reject; retain reproducibility and publish limitations | OUT |
| ID classifier / duplicate entity detection | PARTIAL | No ground truth or declared key | Evidence only; no new role-based defect rules | OUT |
| Model training, leakage/fairness/schema checks | OUT OF SCOPE | Would imply task knowledge not supplied | Document boundaries; no platform expansion | OUT |

Implemented: empty/no-finite chart guards; severity-derived review status; column missingness overview; shared fact/rule/interpretation presentation; explicit severity boundaries; local parser counts/examples and ID hints; small-sample and statistical caveats; score-policy rationale. The score formula, detection thresholds, and ranking remain unchanged. Profile 1.1 adds evidence and cautious semantic labels; score policy stays 1.0. The regression suite caught a newly added column name entering the summary payload during development; explicit summary and issue allowlists now prevent this and protect future local evidence fields.

## Final self-interview

**1. What does Data QA Agent promise?**

It surfaces common structural and statistical signals in one CSV and makes them auditable: observations, detection rules, severity rules, and conditional interpretation. It helps decide what deserves review. It neither certifies data nor establishes fitness for a particular modeling task.

**2. Why exist instead of using `pandas.describe()`?**

The product is a review workflow around deterministic statistics: reproducible rules and priorities, an explicit penalty policy, concise modeling implications, and a report. A notebook can implement those checks too; the value is packaging the policy and explanations consistently for a quick first inspection, not inventing new statistical methods.

**3. What is deterministic and what is delegated?**

Loading, statistics, flags, severity, ranking, score, review status, parsing evidence, and authored fallback guidance are code-controlled. The LLM receives allowlisted aggregates and anonymous aliases and produces only explanation, possible modeling impact, suggested remediation, and score commentary. Responses are validated and never merged into authoritative facts. Free text can still be wrong, so it is labeled interpretation.

**4. What can the score not tell you?**

It cannot tell whether a dataset is semantically correct, unbiased, leakage-free, causally informative, representative, or ready for training/production. It is not a probability or a percentage of valid data. It may be high despite a critical individual finding; schema width and overlapping signals affect the penalty arithmetic. Findings and denominators take precedence over the headline number.

**5. What are the three most important tradeoffs?**

1. Transparent fixed rules are auditable and reproducible, but weights are uncalibrated and generic thresholds generate false positives. Keep the policy explicit rather than claim a universal metric.
2. No target, key contract, or domain model makes first-pass inspection easy, but prevents conclusions about identifier roles, leakage, legitimate repeats, or business validity. Do not manufacture that context.
3. Optional aggregate-only LLM explanation provides adaptable prose without making calculations depend on a provider, but loses raw context and still requires human judgment. Authored guidance and export keep the tool useful offline.

Execution evidence, including adversarial UI cases, the browser check, and the single live-provider call, is recorded in [VALIDATION.md](../VALIDATION.md). No usability study establishes the 60-second goal, and no outcomes study calibrates the score.
