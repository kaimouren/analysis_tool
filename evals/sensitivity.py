"""Boundary observations and real-frame curves; policy, not statistical calibration."""
import json
from pathlib import Path
import sys
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from policy import DEFAULT_THRESHOLDS
from qa_core import profile_dataframe, severity


def run():
    bands = []
    for kind in ("missingness", "duplicates", "outliers", "mixed_type"):
        settings = DEFAULT_THRESHOLDS.bands(kind)
        for level, boundary in settings.items():
            if boundary is None:
                continue
            for position, value in [("below", max(0, boundary-.001)), ("equal", boundary),
                                    ("above", boundary+.001), ("substantially_above", min(99, boundary+20))]:
                bands.append({"check": kind, "boundary_level": level, "boundary": boundary,
                              "position": position, "value": value,
                              "severity": severity(value, **settings) if value > 0 else "not detected"})
    curves = []

    def record(name, setting, frame, policy=DEFAULT_THRESHOLDS):
        p = profile_dataframe(frame, thresholds=policy)
        curves.append({"case": name, "setting": setting, "score": p["quality_score"],
                       "penalties": p["score_breakdown"],
                       "issues": [(i["issue_type"], i["column"], i["severity"], i["rank"]) for i in p["issues"]],
                       "semantic_type": p["columns"][0]["semantic_type"], "context_notes": p["context_notes"]})
        curves[-1]["column_observations"] = {k: p["columns"][0][k] for k in
                                           ("constant", "near_constant", "possible_id", "id_evidence", "outlier_count", "datetime_parseability_pct")}

    for pct in (4.9, 5, 5.1, 8, 9, 10, 11, 12, 15, 19.9, 20, 20.1, 49.9, 50, 50.1, 80):
        n = round(pct*10)
        record("missingness_pct", pct, pd.DataFrame({"x": [None]*n + list(np.linspace(.01, 1.99, 1000-n)), "anchor": np.linspace(.02, 2.98, 1000)}))
    for count in (94, 95, 96, 99):
        record("concentration_pct", count, pd.DataFrame({"x": ["a"]*count + ["b"]*(100-count), "anchor": np.linspace(.01, 1.99, 100)}))
        record("uniqueness_pct", count, pd.DataFrame({"x": [f"id_{i}" for i in range(count)] + ["id_0"]*(100-count), "anchor": np.linspace(.01, 1.99, 100)}))
        record("date_parseability_pct", count, pd.DataFrame({"x": ["2024-01-01"]*count + ["unknown"]*(100-count), "anchor": np.linspace(.01, 1.99, 100)}))
    for length in (79, 80, 81, 160):
        record("median_text_length", length, pd.DataFrame({"x": ["a"*(length-1)+chr(65+i) for i in range(10)]}))
    for count in (99, 100, 101, 200):
        record("outlier_gate_pct", count/100, pd.DataFrame({"x": list(np.linspace(.01, .99, 10000-count))+[100.]*count, "anchor": np.linspace(.02, 2.98, 10000)}))
    for value in (4.4999, 4.5, 4.5001, 40):
        record("upper_iqr_fence_4_5", value, pd.DataFrame({"x": [0.]*25+[1.]*25+[2.]*25+[3.]*24+[value]}))
    frame = pd.DataFrame({"x": [0., 1., 2., 3., 100.], "anchor": np.linspace(.01, 1.99, 5)})
    for parameter, values in (("iqr_multiplier", (1.49, 1.5, 1.51, 3)), ("outlier_score_scale", (4.99, 5, 5.01, 10))):
        for value in values:
            record(parameter, value, frame, replace(DEFAULT_THRESHOLDS, **{parameter: value}))
    for n in (19, 20, 21, 40):
        record("small_sample_and_sequence_rows", n, pd.DataFrame({"x": range(n)}))
    return {"percentage_band_probes": bands, "real_frame_curves": curves}


if __name__ == "__main__":
    result = run()
    (Path(__file__).parent / "sensitivity-results.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(f"Recorded {len(result['percentage_band_probes'])} band probes and {len(result['real_frame_curves'])} real-frame curves.")
