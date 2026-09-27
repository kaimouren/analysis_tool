# Fictional export-like fixtures

All CSVs are local fictional constructions, not downloaded customer data. `example.invalid` addresses are placeholders. No network access is used by evaluation.

- `crm.csv`: 20 constructed customers plus two exact repeats; mixed ID formatting, optional emails, casing/whitespace and malformed dates.
- `orders.csv`: 20 orders plus two repeats; missing customer IDs, legitimate possible refunds, large numeric amounts, currency text and timezone/date inconsistencies.
- `survey.csv`: 20 responses plus two repeats; Likert values, whitespace comments, free text, inconsistent category spelling, optional fields and a valid constant cohort.
- `events.csv`: 100 events plus two repeats; nearly unique event IDs, future test timestamps, optional mobile property and mixed duration tokens.
- `financial.csv`: 20 journal-style rows; comma/parenthesis/negative formatting, missing amounts, numeric extremes, unique references and constant currency metadata.

`evals/behavioral.py` defines required observations separately from allowed ambiguous warnings. Unexpected findings require review; they are not automatically domain errors. The first run surfaced a constant `property` warning in events: every non-null value is deliberately `mobile`. Reviewing the fixture establishes that this is a legitimate observed constant, so it is explicitly listed as ambiguous rather than silently modifying the detector or calling the warning a false positive. Required findings, ambiguous warnings, misses and extras remain separate in the result artifact.

The realistic shape does not make these real-world labeled ground truth. This suite measures scenario behavior and regression coverage, not accuracy. It cannot establish that a negative adjustment, repeated event, constant metadata field, high-cardinality name or future test timestamp is incorrect. Cautious report language is tested separately in `tests/test_v1_1.py`.
