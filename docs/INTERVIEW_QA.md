# Technical interview Q&A

## 1. Why not let the LLM calculate statistics?

Counts, rates, and decomposition need reproducible arithmetic and explicit denominators. Python performs these operations; the model chooses analyses. This separates computational correctness from the harder problem of selecting a relevant scope.

## 2. Why bounded tools instead of Python execution?

Eight registered tools provide inspectable contracts and a limited capability surface. The model cannot execute arbitrary code or access a shell, filesystem, or connector. The tradeoff is reduced flexibility: unsupported analyses remain unsupported rather than being improvised.

## 3. Why was real-model success only 19.44%?

Only 21/108 baseline runs met all scenario requirements under the recorded GPT-4o-mini / planner-v2.1 configuration. Failures included missing evidence, incorrect scopes, wrong analysis classes, premature stopping, and unrecovered errors. Success was stricter than the controller's completed status. Synthetic tasks and strict selectors also constrain how broadly this result applies.

## 4. Why is 100% grounding not 100% correctness?

Grounding checks whether final claims map to saved evidence. A correct number can answer the wrong question or omit half the requested work. The recorded 100% covers 255 material claims in 88 claim-bearing runs; it is not a success score for all 108 investigations. Independent replay and task coverage are separate checks.

## 5. How do you detect premature stopping?

Each benchmark scenario declares required evidence, including argument/scope selectors and expected values. A run that stops or consumes a limit before those requirements are satisfied receives a premature-stop label. This benchmark contract can be stricter than the runtime validator's heuristic sufficiency checks.

## 6. How do you evaluate tool selection?

Scenarios declare acceptable tool classes. Selection accuracy measures model calls within those classes; relevance separately measures new required evidence or a question-named diagnostic profile. The evaluator permits different paths, but its class policy can penalize reasonable extra diagnostics. Controlled injected faults are excluded from the model-selection denominator.

## 7. Why repeated runs?

A single successful demo conceals variability. Three repeats exposed six mixed-outcome scenarios, alongside four that passed every repeat and 26 that passed none. Three is still too few to establish strong population bounds; the report preserves per-scenario outcomes instead of relying only on a mean.

## 8. Why not use an LLM judge?

These tasks have fixed fixtures, explicit scopes, and code-authored claims, so deterministic replay can check the required evidence directly. It avoids introducing a second model's variability. It does not solve evaluation of arbitrary prose or open-ended business questions, where another approach might be needed.

## 9. How does the regression gate work?

It compares compatible scenario/repetition manifests and evaluator versions. Unsupported or contradicted claims, altered evidence, grounding below 99%, or a lost successful repeat on any critical scenario fail the gate. Other adverse changes use max(5 percentage points, twice baseline standard error). That is an operational tolerance, not a significance test.

## 10. Why did the candidate prompt get rejected?

Golden success increased from 8/36 to 11/36, but critical conversion_device dropped from 2/3 to 1/3. The critical-scenario rule overrode the aggregate gain. The candidate remains opt-in; planner-v2.1 remains the production default. The small sequential experiment does not establish a causal prompt effect.

## 11. What would you improve next?

In a separately scoped future phase, I would investigate failures around exact time scopes, missing requested analyses, and completion decisions, then evaluate proposed changes on held-out tasks and more repeats. I would also seek domain-owned contracts and representative datasets. None of those improvements is implemented or promised as V2.3/V3 work.

## 12. How do you prevent prompt injection from CSV cells?

There is no raw-row tool; unselected text cells do not enter planner context. Question, schema, and selected group labels remain untrusted. Strict actions, an allowlisted registry, copied contexts, and code-authored final claims constrain the impact. Injection can still distract planning within permitted analyses, so the project does not claim universal resistance.

## 13. How do you handle unsupported premises?

Deterministic comparisons classify supported directional premises, contradictions, or inconclusive cases using narrow language/sign rules and eligibility checks. A contradicted primary period comparison can stop without inventing an explanation. These are bounded heuristics, not general natural-language entailment or a guarantee that every false premise is recognized.

## 14. How do you avoid causal claims?

Investigation renders code-authored descriptive claims rather than accepting generated causal prose. Segment contributions describe arithmetic changes in observed data. The UI and docs explain that a largest observed contributor does not establish the underlying cause. Optional QA/comparison prose has a weaker boundary and is explicitly qualified.

## 15. What are the biggest benchmark limitations?

Manually designed synthetic tasks, three repeats, strict scope selectors, accepted-class policy, an unpinned model alias, and provider/concurrency variation limit generalization. Recovery probes inject declared faults rather than measuring only spontaneous mistakes. Estimated cost is unavailable, and structured claim validation is not a universal semantic correctness test.

## 16. Can forged evidence fool the evaluator?

The evaluator replays the saved tool call against the fixture and checks linkage, arguments, and values. A forged answer agreeing with a forged ledger is insufficient. Artifact validation also rejects incompatible versions, changed contracts, duplicate identities, non-finite metrics, and incomplete captures from passing regression gates.

## 17. What does offline CI prove after a prompt change?

It verifies deterministic tools, controller regressions, evaluator behavior, and saved-trajectory replay. It cannot measure decisions a changed prompt would now produce. Fresh real-model captures are needed for that; a separate manual workflow supports them without making normal CI depend on a paid provider.

## 18. How would you deploy a safe public demo?

Use app.py on Python 3.11 with requirements.txt, omit server API credentials, and leave QA_HISTORY_PATH unset. QA and comparison work without a key; investigation shows guidance and disables execution. Uploaded data is held in session state rather than a shared dataset cache. This is not a tenant-isolation or production-capacity guarantee. Public deployment remains unverified until the actual URL is smoke-tested.

Sources: [evaluation contracts](AGENT_EVALUATION.md), [investigation design](INVESTIGATION.md), [case study](AGENT_RELIABILITY_CASE_STUDY.md), and [validation](../VALIDATION.md).
