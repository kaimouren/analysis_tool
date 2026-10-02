# LLM failure modes

V2.1 investigation has a different boundary: the model emits tool actions and
evidence selections, while code renders all factual claims. It rejects free-form
answers instead of extending the V1/V2 lexical prose filter. This prevents prose
fabrication but cannot prove that selected metrics/scopes answer the intended
question. The historical optional-prose limitations below remain unchanged for
QA/comparison. See [V2.1 red-team record](V2_1_RED_TEAM.md), including one partial
and one successful synthetic live investigation.

V1.1 tests the explanation trust boundary with mocked responses, not a live-model quality study. Findings, severities, ranking and score remain code-owned and are checked unchanged for every prose attack. The prompt is an instruction, not proof of compliance.

| Attack | V1 behavior | V1.1 behavior / remaining gap |
|---|---|---|
| Invented `secret_revenue` column | Accepted | Underscore identifiers rejected; invented ordinary-language `revenue column` still passes |
| Invented statistic `99 percent` | Rejected by digit check | Still rejected; spelled-out quantities are not generally detected |
| `The root cause is ...` | Accepted | Explicit root-cause/caused-by phrases rejected; `The exporter lost these fields during migration` still passes |
| `Delete all ... and retain every ...` | Accepted | Blanket destructive phrases rejected; paraphrased contradictions still pass |
| `guaranteed`, `definitely`, `certainly` | Accepted | These certainty markers rejected; `Every observation is accurate` still passes |
| Prompt injection in CSV cells/headers | Excluded from payload | Explicit test confirms content and real column names remain excluded |
| Missing parsed response, malformed structure, extra facts | SDK/schema or identity validation rejects | Trust boundary revalidates the supplied structure; safe fallback tested |
| Overlength prose | SDK schema normally rejects network responses, but a mutated model instance bypassed direct validator bounds | Revalidate `model_dump()` at the boundary; mutated 901-character text now fails |
| Wrong/reordered/missing issue identity | Rejected | Still rejected; deterministic ranking is retained |
| Provider timeout/refusal/error | Authored fallback | Still fallback, categorical content-free log, no profile changes |

The new phrase checks are intentionally narrow fail-closed screening for clear violations, not a semantic verifier. They can reject benign discussion of invalidity or causation, including a negated phrase; that is acceptable only because authored guidance is always available. They can miss paraphrases, invented facts without digits, spelled-out confidence claims and nuanced contradictory advice. Tests deliberately retain known bypasses as visible limitations rather than implying complete hallucination prevention.

Provider requests now cap completion tokens at 2,000. Combined with top-five identity checks and per-field 900-character limits, this bounds accepted explanatory content. Providers that reject this parameter or truncate output use the existing fallback; compatibility is not assumed. This is not a network response-byte cap or protection from a malicious approved provider. No new live call was necessary for this pass.

The UI labels generated prose and renders it as plain text. Reports distinguish observed facts, structured evidence, severity rules, authored guidance and AI interpretation. If a generated statement disagrees with deterministic fields, those fields remain authoritative; rejection occurs where the lexical/schema rules can detect the violation. Uncaught contradictions are a known reason to review or use the default authored guidance. No automated remediation executes suggestions.

Run `python -m pytest tests/test_v1_1.py -q` plus the existing explanation tests. The tests exercise both caught attacks and deliberately accepted semantic gaps; they do not measure a provider's factual accuracy, usefulness or latency distribution.
