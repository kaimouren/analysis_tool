# Test effectiveness: controlled mutations

Run `python tests/mutation_check.py`. The harness copies source/tests/fixtures into one temporary directory per mutation, applies exactly one textual defect there, and runs its targeted pytest assertion. It never edits the working source. Temporary paths are resolved under their allocated directory. A kill requires pytest exit 1 and an actual AssertionError; collection/import failures do not count.

| Injected defect | Targeted assertion | Result |
|---|---|---|
| boundary | `tests/test_v1.py::test_every_percentage_severity_boundary` | Caught: 2 failed, 2 passed in 13.87s |
| penalty | `tests/test_qa.py::CoreTests::test_hand_calculated_statistics` | Caught: 1 failed in 17.06s |
| duplicates_disabled | `tests/test_qa.py::CoreTests::test_duplicate_denominator` | Caught: 1 failed in 9.94s |
| severity_swapped | `tests/test_qa.py::CoreTests::test_semantics_and_boundaries` | Caught: 1 failed in 11.19s |
| report_evidence_removed | `tests/test_v1_1.py::test_export_has_structured_evidence_for_every_finding` | Caught: 1 failed in 4.45s |

All five deliberate defects were caught: making a critical boundary exclusive, zeroing the missingness cap, disabling duplicates, returning low in place of high severity, and removing structured evidence from the report. The first four are covered by existing V1 assertions. The explicit all-issue structured-evidence assertion was added in V1.1: the earlier report test checked evidence-adjacent wording, not the JSON evidence block itself. This is a concrete coverage improvement rather than a test-count claim.

The suite also asserts intentional limitations: paraphrased model falsehoods can pass; high scores coexist with critical findings; formatting-only issues are unscored; CSV inference normalizes tokens. Passing these tests means behavior is explicit and stable, not that the limitations are solved.

This is a five-mutation manual effectiveness probe, not an exhaustive automated mutation score. It does not prove every branch, concurrency interleaving, provider behavior or deployment failure is covered. Tests and evaluation fixtures are authored by the same project and share assumptions; independent domain review remains valuable. No intentional defect is committed.
