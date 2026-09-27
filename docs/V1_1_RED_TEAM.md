# V1.1 adversarial review

Baseline: `dca9d03`. Ratings below describe inspected V1 behavior, not documentation polish. Reproduced numerical and LLM probes precede fixes. Final remediation evidence is appended after validation; baseline counts are intentionally retained.

Baseline ratings: PASS: 18, WEAK: 18, FAIL: 4, OUT OF SCOPE: 4.

| # | Rating | Interview question | Implementation evidence |
|---|---|---|---|
| 1 | PASS | Are facts independent of a provider? | qa_core has no provider calls; offline tests assert scores. |
| 2 | PASS | Can model output overwrite score or severity? | ExplanationBundle exposes prose and issue IDs only. |
| 3 | WEAK | Can generated prose invent columns? | validate_explanations only blocks column_ aliases/digits; secret_revenue passes. |
| 4 | WEAK | Can it assert an unsupported root cause? | The root cause is a broken production database passes the validator. |
| 5 | WEAK | Can it contradict its own recommendation? | Delete all records and also retain every record passes. |
| 6 | FAIL | Are response bounds enforced after construction? | Assignment of 1,000 characters to a Pydantic instance passes validate_explanations. |
| 7 | PASS | Are unknown/reordered issue identities rejected? | tests/test_qa.py and test_deployment.py exercise rejection. |
| 8 | PASS | Can uploaded prompt injection enter the payload? | explanation_payload explicitly omits values and real names. |
| 9 | PASS | Do provider failures preserve profiling? | Mock failure/timeout tests preserve the profile and authored guidance. |
| 10 | PASS | Is score arithmetic reproducible? | Hand-calculated 73.5 case and repeated JSON assertions. |
| 11 | WEAK | Are score differences calibrated? | PENALTY_CAPS are authored policy; no outcome labels or calibration. |
| 12 | WEAK | Does displaying 92.36 suggest unjustified precision? | app.py formats the headline with .2f; arithmetic precision exceeds interpretive precision. |
| 13 | PASS | Can a critical finding coexist with a high score? | 99 clean columns plus null column test asserts 99.7 and critical status. |
| 14 | WEAK | Are width comparisons meaningful? | Cell/column means dilute local defects; only one wide adversarial test exists. |
| 15 | WEAK | Are overlapping penalties counted separately? | score_dataset sums missing/constant/ID/outlier terms with no causal deduplication. |
| 16 | WEAK | Can tiny threshold crossings reorder priorities? | Inclusive severity bands and 1% IQR score gate exist; no full sensitivity artifact. |
| 17 | PASS | Are severity thresholds centralized? | policy.py frozen validated dataclass; override regression test. |
| 18 | PASS | Are constant and near-constant exclusive? | profile_column explicitly excludes constant before near_constant. |
| 19 | WEAK | Does evaluation reflect realistic export ambiguity? | evals/datasets.py contains eight small constructed cases only. |
| 20 | WEAK | Are legitimate suspicious cases tested for cautious language? | Caveats exist but no dedicated legitimate-case suite. |
| 21 | PASS | Is duplicate counting well defined? | DataFrame.duplicated after first, denominator tests. |
| 22 | OUT OF SCOPE | Does it validate entity identity or declared keys? | No key contract or business-schema input exists. |
| 23 | OUT OF SCOPE | Does it infer whether negative money is invalid? | No business semantics are inferred. |
| 24 | WEAK | Are CSV representation changes visible at the point of use? | README warns about NA/zeros; upload UI still says dataset never modified without parser qualification. |
| 25 | FAIL | Are large-integer extrema exact? | 9007199254740993 reports min 9007199254740992 after float conversion. |
| 26 | FAIL | Can finite numerical input overflow summaries? | 1e308 through 1.3e308 emit overflow warnings and inf mean/std. |
| 27 | PASS | Are duplicate/blank headers rejected? | ingestion.py inspects headers before pandas; tests cover both. |
| 28 | PASS | Are binary uploads rejected safely? | Control-byte regex and safe InputValidationError; no execution/deserialization. |
| 29 | WEAK | Can a single huge cell consume disproportionate work? | A 300,000-character cell is accepted; only file/frame limits exist. |
| 30 | PASS | Are row/column/cell limits enforced without sampling? | Bounded read plus validate_frame; limit tests. |
| 31 | WEAK | Have string-heavy and duplicate-heavy costs been measured? | Benchmark uses one mixed eight-column distribution only. |
| 32 | FAIL | Is concurrent behavior supported by measurement? | No concurrency harness or shared-state measurement at dca9d03. |
| 33 | WEAK | Are warnings filters safe under threaded analysis? | warnings.catch_warnings changes process-wide filters in Python 3.11; concurrent parsing untested. |
| 34 | PASS | Are uploads persisted by application code? | Loader uses StringIO; session state stores frames; no upload writes. |
| 35 | PASS | Are server credentials isolated from visitor endpoints? | Own-key rule plus exact administrator allowlist and tests. |
| 36 | WEAK | Can visitors amplify paid API calls? | Button-triggered requests, no quotas or rate limiting. |
| 37 | PASS | Are diagnostic fields content-free? | events.py rejects unapproved fields and raw reasons; redaction test. |
| 38 | WEAK | Is public-hosting readiness operationally verified? | No public deployment or multi-user browser evidence. |
| 39 | PASS | Was a clean install tested? | V1 separate .venv-clean tests and real browser; recorded commands. |
| 40 | WEAK | Does CI check dependency consistency? | tests.yml runs tests/lint/eval but omits pip check. |
| 41 | WEAK | Have tests been demonstrated to catch injected defects? | No mutation evidence; pass count alone cannot establish effectiveness. |
| 42 | OUT OF SCOPE | Does it offer historical drift or monitoring? | No persistence/history model; deliberately deferred. |
| 43 | OUT OF SCOPE | Does it support ten million rows? | Bounded in-memory engine; input guards reject this scale. |
| 44 | PASS | Does export include evidence and all recommendations? | report.py emits Structured evidence and all authored issue guidance; integration tests. |

## WEAK / FAIL decisions

### 3. Can generated prose invent columns?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: validate_explanations only blocks column_ aliases/digits; secret_revenue passes. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add narrow identifier/claim checks and document uncaught prose; no claim of semantic verification.

### 4. Can it assert an unsupported root cause?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: The root cause is a broken production database passes the validator. Fix in V1.1: yes, within the existing product boundary. Proposed action: Reject explicit certainty/root-cause phrases; demonstrate bypasses.

### 5. Can it contradict its own recommendation?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Delete all records and also retain every record passes. Fix in V1.1: yes, within the existing product boundary. Proposed action: Reject explicit destructive blanket advice; leave general contradiction detection unclaimed.

### 6. Are response bounds enforced after construction?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Assignment of 1,000 characters to a Pydantic instance passes validate_explanations. Fix in V1.1: yes, within the existing product boundary. Proposed action: Revalidate serialized response at trust boundary and cap provider output.

### 11. Are score differences calibrated?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: PENALTY_CAPS are authored policy; no outcome labels or calibration. Fix in V1.1: measurement/documentation only; underlying capability deferred. Proposed action: Preserve weights; characterize ten adversarial cases and disclaim calibration.

### 12. Does displaying 92.36 suggest unjustified precision?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: app.py formats the headline with .2f; arithmetic precision exceeds interpretive precision. Fix in V1.1: yes, within the existing product boundary. Proposed action: Round headline to whole points, retain precise arithmetic in report audit.

### 14. Are width comparisons meaningful?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Cell/column means dilute local defects; only one wide adversarial test exists. Fix in V1.1: yes, within the existing product boundary. Proposed action: Measure width dilution explicitly.

### 15. Are overlapping penalties counted separately?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: score_dataset sums missing/constant/ID/outlier terms with no causal deduplication. Fix in V1.1: yes, within the existing product boundary. Proposed action: Measure overlap explicitly; preserve policy without invented causal model.

### 16. Can tiny threshold crossings reorder priorities?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Inclusive severity bands and 1% IQR score gate exist; no full sensitivity artifact. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add measured boundary/sensitivity matrix.

### 19. Does evaluation reflect realistic export ambiguity?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: evals/datasets.py contains eight small constructed cases only. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add five offline realistic export fixtures with required versus ambiguous findings.

### 20. Are legitimate suspicious cases tested for cautious language?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Caveats exist but no dedicated legitimate-case suite. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add legitimate-suspicious scenarios and report language assertions.

### 24. Are CSV representation changes visible at the point of use?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: README warns about NA/zeros; upload UI still says dataset never modified without parser qualification. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add visible parser-normalization caveat and inference probe artifact.

### 25. Are large-integer extrema exact?

Why it matters: incorrect numeric evidence or unbounded/shared resource behavior undermines reliability. Evidence: 9007199254740993 reports min 9007199254740992 after float conversion. Fix in V1.1: yes, within the existing product boundary. Proposed action: Preserve exact extrema and disclose approximate float summaries.

### 26. Can finite numerical input overflow summaries?

Why it matters: incorrect numeric evidence or unbounded/shared resource behavior undermines reliability. Evidence: 1e308 through 1.3e308 emit overflow warnings and inf mean/std. Fix in V1.1: yes, within the existing product boundary. Proposed action: Reject unsupported extreme native numeric magnitudes with actionable error.

### 29. Can a single huge cell consume disproportionate work?

Why it matters: incorrect numeric evidence or unbounded/shared resource behavior undermines reliability. Evidence: A 300,000-character cell is accepted; only file/frame limits exist. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add bounded field-length validation without increasing limits.

### 31. Have string-heavy and duplicate-heavy costs been measured?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Benchmark uses one mixed eight-column distribution only. Fix in V1.1: yes, within the existing product boundary. Proposed action: Measure resource scenarios in isolated processes.

### 32. Is concurrent behavior supported by measurement?

Why it matters: incorrect numeric evidence or unbounded/shared resource behavior undermines reliability. Evidence: No concurrency harness or shared-state measurement at dca9d03. Fix in V1.1: yes, within the existing product boundary. Proposed action: Measure 2/5/10 simultaneous in-process analyses; label limits of proxy.

### 33. Are warnings filters safe under threaded analysis?

Why it matters: incorrect numeric evidence or unbounded/shared resource behavior undermines reliability. Evidence: warnings.catch_warnings changes process-wide filters in Python 3.11; concurrent parsing untested. Fix in V1.1: yes, within the existing product boundary. Proposed action: Serialize warning-filter sections; test concurrent outcomes.

### 36. Can visitors amplify paid API calls?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: Button-triggered requests, no quotas or rate limiting. Fix in V1.1: measurement/documentation only; underlying capability deferred. Proposed action: Document cost amplification; quotas/identity out of scope.

### 38. Is public-hosting readiness operationally verified?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: No public deployment or multi-user browser evidence. Fix in V1.1: measurement/documentation only; underlying capability deferred. Proposed action: Document deployment gates and honest unverified status.

### 40. Does CI check dependency consistency?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: tests.yml runs tests/lint/eval but omits pip check. Fix in V1.1: yes, within the existing product boundary. Proposed action: Add pip check and local structural workflow validation.

### 41. Have tests been demonstrated to catch injected defects?

Why it matters: an unsupported confidence or operational claim can mislead users and interviewers. Evidence: No mutation evidence; pass count alone cannot establish effectiveness. Fix in V1.1: yes, within the existing product boundary. Proposed action: Run five isolated deliberate mutations and require intended assertion failures.

## Scope

No weight calibration, public deployment, distributed execution, data contracts, identity or quotas will be invented. Strictly distinguish exact measurements, arithmetic policy behavior, heuristic interpretation and unverified operational guarantees.

## Post-hardening verdict

Final classification of the same 44 questions: **33 PASS, 7 WEAK, 0 FAIL, 4 OUT OF SCOPE**. This is an engineering review rubric, not an accuracy metric.

- PASS after remediation: 6 (response revalidation), 12 (headline precision), 14-16 (width/overlap/sensitivity evidence), 19-20 (export ambiguity and language tests), 24-26 (inference visibility, exact parsed extrema and safe numeric range), 29 (cell guard), 31 (resource measurements), 33 (full public-entry serialization), 40 (CI dependency consistency), 41 (five mutation kills).
- Still WEAK: 3, 4 and 5 (semantic invented facts/causes/contradictions can be paraphrased around lexical checks); 11 (no score calibration); 32 (measured threads are not real multi-browser hosting validation); 36 (no API quotas); 38 (no public deployment evidence).
- OUT OF SCOPE remains 22, 23, 42 and 43: entity contracts, inferred business semantics, historical monitoring and ten-million-row execution.
- Original PASS items remain covered by the preserved V1 tests plus new regression assertions.

The numerical bug and warning-filter concurrency failure were reproduced in code, not merely inferred from docs. See CSV_INFERENCE.md, CONCURRENCY.md and TEST_EFFECTIVENESS.md. Evidence supports a candid local-tool interview defense; it does not support claims of calibrated data validity, verified semantic AI output or production multi-tenant readiness.
