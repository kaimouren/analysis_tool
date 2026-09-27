# Scoring stress test

Run `python evals/stress.py --output evals/stress-results.json`. Ten fixed frames deliberately challenge the interpretation of score policy 1.0. Complete column-level findings, severities and penalty arithmetic are in the JSON artifact. Scores below are exact policy arithmetic; UI headlines now round to whole points.

| Case | Findings by type (count) | Nonzero penalties | Score | Interpretation |
|---|---|---|---:|---|
| one_critical_column | missingness: 1 | missingness: 9.0 | 91.0 | A critical local coverage problem averages to a high aggregate score. |
| hundreds_of_advisory_findings | blank_strings: 199, case_variants: 199, surrounding_whitespace: 199 | None | 100.0 | 597 formatting warnings are intentionally unscored, not evidence of clean data. |
| overlapping_cells | missingness: 1, near_constant: 1, outliers: 1 | missingness: 7.5, outliers: 0.5, near_constant: 2.5 | 89.5 | Missingness, concentration and IQR penalties overlap in one feature. |
| one_unusable_of_200 | missingness: 1 | missingness: 0.15 | 99.85 | A completely empty feature is diluted by 199 clean columns. |
| widespread_moderate_missingness | missingness: 9 | missingness: 5.4 | 94.6 | Nine columns at 20% missingness still lose only 5.4 points. |
| severe_duplicates | duplicates: 1, outliers: 1 | duplicates: 17.8, outliers: 7.5 | 74.7 | 89 exact repeats and ten IQR flags overlap; repeated weighting drives both. |
| single_row | constant: 1, possible_id: 1 | constant: 15.0, possible_id: 3.0 | 82.0 | One observed value is both constant and ID-like; inference is unstable. |
| very_wide_clean | None | None | 100.0 | Width alone is unpenalized; no implemented findings does not certify correctness. |
| highly_sparse | missingness: 9 | missingness: 24.3 | 75.7 | Ninety-percent missingness in nine columns still leaves a score in the seventies. |
| legitimate_constant_metadata | constant: 1 | constant: 7.5 | 92.5 | Valid metadata attracts a constant penalty without a feature-role contract. |

## Mathematical conclusions

- **Double counting:** yes. Correlated properties of one feature can attract separate penalties. The overlap case pays 7.5 missingness + 2.5 near-constant + 0.5 IQR = 10.5. This is not a count of distinct errors. The single-row case is both constant and ID-like.
- **High score with critical findings:** yes, 99.85 with one fully empty column out of 200. This follows intentional cell/column averaging, not a bug in addition. As a claim of dataset fitness it would be misleading; the independent review status and explicit findings are essential.
- **Different widths:** not generally comparable. Adding clean columns dilutes localized penalties; adding unscored formatting findings does not change the score at all.
- **Different row counts:** prevalence-based terms avoid a raw row-count penalty, but comparability requires comparable schemas, distributions and policies. Repeating a dataset changes duplicate prevalence, small samples change quantiles and cardinality, and a single-row interpretation is unstable. There is no unconditional size invariance.
- **92.36:** the planted sample's default weighted penalties sum to 7.64 after category rounding. It does not mean 92.36 percent valid, ready or accurate. It is a deterministic arithmetic result from this policy.
- **92 versus 88:** trust only that the same implemented formula produces different penalty totals. Without matched schema, effective policy and domain context, do not infer that the first dataset is better. Even with those held fixed, the magnitude has no calibrated outcome meaning.
- **Ordinal, approximate or calibrated?** An approximate policy index useful for within-context triage, not a universal ordinal ranking and not a calibrated measure. No mathematical evidence justifies changing weights simply to produce more intuitive scores.

## Presentation decision

Keep exact two-decimal arithmetic in the profile, penalty audit and report for reproducibility. Round the headline to whole points and label its interpretation approximate. A displayed 100 can be a rounded 99.85 with a critical issue; rounding is not a fix for aggregation. Review status remains separate and is never derived from score bands. CSV inference and floating-point limitations are explicit. Score weights and thresholds are unchanged.

## Oracle review

Expectations were authored independently. Two initial hand totals were corrected after checking the formula: the overlap penalty is 10.5, not 10.2; 89 duplicate rows cost 17.8 and ten outliers cost 7.5, totaling 25.3. No detector rule was changed to match expectations. The JSON preserves every final finding and penalty rather than only an attractive summary metric.
