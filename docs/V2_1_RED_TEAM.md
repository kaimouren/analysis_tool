# V2.1 red-team record

Scope: deterministic tool/controller attacks, scripted action attacks, Streamlit
integration and two small synthetic live runs. This is not a penetration test or
an estimate of all prompt-injection attacks against a provider.

| Probe / finding | Resolution and evidence |
|---|---|
| Whole-dataset quality could satisfy a temporal question; quality alone could satisfy a metric-plus-quality question | Tightened sufficiency; dedicated early-stop tests |
| Later unrelated contradicted metric could bypass an earlier supported why question | First eligible comparison anchors required matching decomposition; adversarial test |
| Model requests nonexistent columns / date fields / unsupported aggregation | Structured failure and explicit recovery; no silent substitution; evals 16–20 |
| Same tool and normalized arguments repeated indefinitely | Deduplicate before execution, charge attempt/error budgets; only bootstrap executes in spam test |
| Invented citations, numerical prose, causal/significance prose or hidden rationale | Strict action schema rejects prose; citation validation rejects missing IDs; final claims rendered from code ledger |
| Planner mutates its context to forge a fact | Deep-copied context; authoritative ledger unchanged in regression |
| Model omits contradictory evidence when finishing | Include all primary evidence automatically, tested independently |
| Group records and claims used different sort orders | Both use relevance order; explicit consistency assertion |
| Binary rates were labeled with count units | Proportion units and percentage-point deltas made explicit |
| Integer `1` and string `"1"` could become indistinguishable group labels | Reject ambiguous typed groups; no silent merge or duplicate displayed identity |
| String conversion could make missing cells impersonate a literal `"None"` category | Filter/category-presence comparisons explicitly exclude missing cells before string equality; regression asserts both counts and filtered scope |
| Giant labels/cardinality/context/results | Predeclared bounds and structured failures; output-limit recovery tested |
| Zero net change, missing groups, different populations and tail collapse | Explicit additive formula, null undefined shares and reconciliation; analytical fixtures |
| Empty periods, invalid ISO strings, timezone boundary, all-null/tiny/non-finite/extreme metrics | Explicit errors or ineligible evidence; no invented denominator/sample; tests and evals |
| Next-year Jan 1 exception could apply to a start boundary | Restricted the exception to exclusive endpoints; regression covers both accepted year-end and rejected unstated-year starts |
| CSV cell says to read secrets or claim significance | Unselected cells excluded from planner; no environment/filesystem tool; UI renders text, not data-driven HTML |
| SDK unavailable or exception includes sensitive text | Generic failure, no exception contents, no fake agent fallback |
| New input or failed rerun could leave old evidence download | Clear session result before rerun/on changed question or file; AppTest and browser checks |

## Real-provider observations

First synthetic run used a deliberately short four-step/two-error smoke budget.
It ended **partial**, step limit, after four steps, three tool calls and two
validation errors (30.203s). The original sanitized summary did not retain error
types, so their precise cause is **unknown**. Do not infer a proven recovery bug
or hide this run.

Second synthetic run used the product's normal eight-step/eight-call/three-error
limits. It completed in **three planning steps**, **three tool calls** (including
bootstrap schema), **zero errors**, **22.031s**: period comparison, segment
comparison, evidence selection. This demonstrates one successful real tool loop;
it does not demonstrate error recovery in a real provider run or establish a
model accuracy rate. Scripted recovery tests are reported separately.

## Remaining exposure

The model can choose a valid but irrelevant metric, contrast or filter; narrow
question/sufficiency heuristics do not prove semantic relevance or cover every
language. An injected schema/group label may influence that choice within the
registry. All such arguments and primary evidence remain inspectable. Valid
aggregates/labels can reveal sensitive facts, and sending them requires consent.
No causal/significance capability, differential privacy, hard worker deadline,
network byte cap, per-user quota or multi-tenant admission control was added.
Typed result bounds constrain accepted content, not a malicious approved SDK or
provider. V1/V2 optional-prose limitations remain unchanged.
