# Threshold sensitivity

Run `python evals/sensitivity.py`. The artifact contains 40 isolated percentage-band probes (below, equal, above and substantially above all ten band boundaries) plus 52 actual-frame curves. The zero mixed-type boundary is a detection gate: zero is not a finding and no negative percentage exists. All other positive severity boundaries are inclusive.

## What each default means

| Parameter | Classification | Boundary / effect |
|---|---|---|
| Missingness 5/20/50 percent | Configurable engineering heuristic | Severity jumps at each band; missingness penalty changes proportionally |
| Duplicates 2/10/30 percent | Configurable engineering heuristic | Severity/rank jumps; duplicate penalty changes proportionally |
| Outliers 1/10 percent | Configurable engineering heuristic | Severity changes; 1 percent also gates score eligibility |
| Mixed minority >0 / 10 percent | Configurable engineering heuristic | Mixed detection introduces a whole per-column penalty; minority prevalence changes severity, not penalty size |
| Concentration >=95 percent | Configurable engineering heuristic | Near-constant appears; constants excluded; finite per-column score jump |
| ID uniqueness >=95 percent | Configurable engineering heuristic | Eligible column adds advisory ID penalty; role not established |
| Date parsing >=95 percent | Configurable engineering heuristic | Changes descriptive semantic label, not mixed-parser finding or its score |
| Median text length >80 | Configurable engineering heuristic | Long text loses possible-ID eligibility, potentially increasing score |
| IQR multiplier 1.5 | Configurable conventional statistical rule | Uses quartiles/central spread, but is not a calibrated error probability or significance test |
| Outlier scoring gate 1 percent / scale 5 | Configurable engineering heuristic | Gate is discontinuous; scale saturates cap at 20 percent pooled prevalence |
| Small-sample notice <20 rows | Configurable engineering default | Context only; not a statistical power calculation |
| Sequence hint >=20 unique integers | Configurable engineering default | Descriptive evidence only; no extra score/severity |
| Constant unique count =1, infinity count >0 | Exact observed predicates | Fixed issue-class severity; business interpretation remains uncertain |
| Top values 15, examples 3, example chars 80 | Presentation/privacy limits | Bounded evidence, not statistical thresholds |
| Input dimensions, cell length, numeric range | Resource/numerical engineering guards | Reject unsupported inputs; not quality judgments |

## Observed curves

These rows are actual profiler runs; full issue order and penalties are in `evals/sensitivity-results.json`.

| Case | Setting | Score | Ordered findings (type / severity) |
|---|---:|---:|---|
| missingness_pct | 4.9 | 99.27 | missingness/low |
| missingness_pct | 5 | 99.25 | missingness/medium |
| missingness_pct | 5.1 | 99.23 | missingness/medium |
| missingness_pct | 8 | 98.8 | missingness/medium |
| missingness_pct | 9 | 98.65 | missingness/medium |
| missingness_pct | 10 | 98.5 | missingness/medium |
| missingness_pct | 11 | 98.35 | missingness/medium |
| missingness_pct | 12 | 98.2 | missingness/medium |
| missingness_pct | 15 | 97.75 | missingness/medium |
| missingness_pct | 19.9 | 97.02 | missingness/medium |
| missingness_pct | 20 | 97.0 | missingness/high |
| missingness_pct | 20.1 | 96.98 | missingness/high |
| missingness_pct | 49.9 | 92.52 | missingness/high |
| missingness_pct | 50 | 92.5 | missingness/critical |
| missingness_pct | 50.1 | 92.48 | missingness/critical |
| missingness_pct | 80 | 88.0 | missingness/critical |
| concentration_pct | 94 | 100.0 | None |
| uniqueness_pct | 94 | 100.0 | None |
| date_parseability_pct | 94 | 94.0 | mixed_type/medium |
| concentration_pct | 95 | 97.5 | near_constant/medium |
| uniqueness_pct | 95 | 98.5 | possible_id/low |
| date_parseability_pct | 95 | 91.5 | mixed_type/medium, near_constant/medium |
| concentration_pct | 96 | 97.5 | near_constant/medium |
| uniqueness_pct | 96 | 98.5 | possible_id/low |
| date_parseability_pct | 96 | 91.5 | mixed_type/medium, near_constant/medium |
| concentration_pct | 99 | 97.5 | near_constant/medium |
| uniqueness_pct | 99 | 98.5 | possible_id/low |
| date_parseability_pct | 99 | 91.5 | mixed_type/medium, near_constant/medium |
| median_text_length | 79 | 97.0 | possible_id/low |
| median_text_length | 80 | 97.0 | possible_id/low |
| median_text_length | 81 | 100.0 | None |
| median_text_length | 160 | 100.0 | None |
| outlier_gate_pct | 0.99 | 100.0 | outliers/low |
| outlier_gate_pct | 1.0 | 99.62 | outliers/medium |
| outlier_gate_pct | 1.01 | 99.62 | outliers/medium |
| outlier_gate_pct | 2.0 | 99.25 | outliers/medium |
| upper_iqr_fence_4_5 | 4.4999 | 81.0 | duplicates/critical |
| upper_iqr_fence_4_5 | 4.5 | 81.0 | duplicates/critical |
| upper_iqr_fence_4_5 | 4.5001 | 80.25 | duplicates/critical, outliers/medium |
| upper_iqr_fence_4_5 | 40 | 80.25 | duplicates/critical, outliers/medium |
| iqr_multiplier | 1.49 | 91.0 | outliers/high, possible_id/low |
| iqr_multiplier | 1.5 | 91.0 | outliers/high, possible_id/low |
| iqr_multiplier | 1.51 | 91.0 | outliers/high, possible_id/low |
| iqr_multiplier | 3 | 91.0 | outliers/high, possible_id/low |
| outlier_score_scale | 4.99 | 91.02 | outliers/high, possible_id/low |
| outlier_score_scale | 5 | 91.0 | outliers/high, possible_id/low |
| outlier_score_scale | 5.01 | 90.98 | outliers/high, possible_id/low |
| outlier_score_scale | 10 | 83.5 | outliers/high, possible_id/low |
| small_sample_and_sequence_rows | 19 | 97.0 | possible_id/low |
| small_sample_and_sequence_rows | 20 | 97.0 | possible_id/low |
| small_sample_and_sequence_rows | 21 | 97.0 | possible_id/low |
| small_sample_and_sequence_rows | 40 | 97.0 | possible_id/low |

## Discontinuities and interpretation

Severity labels inevitably jump at configured boundaries; ties and ordering can change immediately. This is a triage policy, not a discontinuity in true data quality. At the IQR scoring gate, 99 flagged values out of 10,000 (0.99 percent) incur zero IQR penalty, while 100 (1 percent) incur 0.375 in the two-numeric-column fixture. At 101 the penalty is 0.37875. The whole-point headline can hide or expose these small arithmetic changes depending on rounding. Ranking depends on type/name when severity ties, not affected-row impact.

Concentration and ID eligibility likewise cause whole per-column penalties to appear or disappear. In mixed-type checks, changing a pure column to even a small mixture introduces the fixed column-fraction penalty; prevalence then affects severity only. Increasing IQR contamination can also move the quartiles and mask extremes, so flagged prevalence need not increase monotonically with contamination. No calibration claim follows from quartile mathematics.

The separate strict-fence experiment keeps Q1=0.75 and Q3=2.25: an upper bound of 4.5 does not flag equality, but flags 4.5001 and 40. The multiplier/scale probes perturb configurable defaults; they are not tuning recommendations. Existing policy remains unchanged because no outcome data justifies alternative cutoffs.
