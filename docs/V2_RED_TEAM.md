# V2 red-team review

The review targeted mathematical boundaries, misleading interpretation, failure recovery and persistence. These are observed engineering checks, not an independent security certification or real-world accuracy estimate.

| Failure or risk | Resolution / evidence |
|---|---|
| Python integers in object columns bypassed the native numeric magnitude guard | Apply the same 1e150 guard to object integer/float scalars; reject larger finite values with a safe error. |
| Converting integer support to float64 could erase drift between adjacent values above 2^53 | KS uses Python numeric ordering and exact parsed extrema. Test adjacent integers near 2^63; moments remain explicitly approximate. |
| Exact decimal TVD cutoff could compute just below 0.10 | Centralized 1e-12 boundary tolerance, tested below/at moderate and at high cutoffs. |
| Float moments can vary with input row order | Canonical sort before scaled moment/quantile calculations; random permutation regression test. |
| Date-only to timestamp-text change could be invisible | Informational representation evidence, separate from coverage change; identical time coverage does not get a risky alert. |
| Irregular dates could invite invented gap expectations | Only an exactly regular baseline with sufficient distinct timestamps enables gap comparison; irregular-baseline negative control. |
| Tiny/empty/all-null datasets could look reassuring | Undefined denominators remain null; empty/no-overlap status is not comparable. Tiny distributions are explicitly unassessed. UI states low drift does not mean healthy and shows assessment coverage. |
| Missingness improvement could be mistaken for worsening | Signed current-minus-baseline pp are preserved; summary measures magnitude, with explicit disclosure that improvements count as drift. |
| Infinity sign changes could disappear when both finite subsets were empty | Separate positive/negative infinity counts and informational change evidence. |
| Model prose could assert causes, significance, numbers or upgraded severity | Reuse structured ID/order/schema checks and lexical guardrails, add drift-specific phrase rejection; mocked malicious outputs fall back without mutating findings. Paraphrase bypass remains a limitation. |
| A safe negated caveat was rejected by literal word guards | Authored fallback uses neutral descriptive wording; document lexical false positives, do not claim semantic validation. |
| Failed recomputation could expose a stale download | Clear prior result/guidance before recomputation and when input identities change; UI and real-browser tests verify removal. |
| A locked database might be mistaken for corruption and renamed | Restrict recovery to SQLite corruption/not-a-database codes. Lock test proves history remains intact. |
| Corrupt JSON metadata with wrong field types could reach UI | Validate record types and skip damaged records with a visible warning. |
| Public history could expose other visitors' filenames | Require administrator environment opt-in, default off; explicit local single-user scope and no uploaded data persistence. |
| Fixed browser debugging port could attach to another local app | Smoke harness allocates its own debugging port and verifies the exact target URL; app test server binds an explicit loopback port. |

Remaining limits: heuristic thresholds and overlapping findings; sample-size-sensitive cardinality; tiny-sample uncertainty; conservative datetime parsing and no business calendar; high-cardinality composition skipped; no multivariate/conditional drift or row matching; numeric moments approximate; input inference remains lossy; no semantic truth guarantee for prose; no tenant isolation, admission control or cloud durability. No true V2 live-provider or public deployment claim is made.
