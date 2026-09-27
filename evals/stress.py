"""Fixed adversarial score observations with independent arithmetic expectations."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from qa_core import profile_dataframe


def cases():
    anchor = np.linspace(.01, 1.99, 100)
    wide = pd.DataFrame({f"feature_{i}": anchor + i/1000 for i in range(199)})
    one_critical = pd.DataFrame({"anchor": anchor, "partial": [None]*60 + list(anchor[:40])})
    minor = pd.DataFrame({f"text_{i}": [" North", "North", "north", " "]*25 for i in range(199)})
    minor["anchor"] = anchor
    overlapping = pd.DataFrame({"anchor": anchor, "overlap": [None]*50 + [0.]*49 + [100.]})
    unusable = wide.copy()
    unusable["unusable"] = None
    moderate = pd.DataFrame({f"feature_{i}": [None]*20 + list(anchor[20:] + i/1000) for i in range(9)})
    moderate["anchor"] = anchor
    duplicates = pd.DataFrame({"x": [.01]*90 + list(np.linspace(.1, 1.9, 10))})
    sparse = pd.DataFrame({f"feature_{i}": [None]*90 + list(anchor[:10] + i/1000) for i in range(9)})
    sparse["anchor"] = anchor
    return {
        "one_critical_column": (one_critical, 91.0, "A critical local coverage problem averages to a high aggregate score."),
        "hundreds_of_advisory_findings": (minor, 100.0, "597 formatting warnings are intentionally unscored, not evidence of clean data."),
        "overlapping_cells": (overlapping, 89.5, "Missingness, concentration and IQR penalties overlap in one feature."),
        "one_unusable_of_200": (unusable, 99.85, "A completely empty feature is diluted by 199 clean columns."),
        "widespread_moderate_missingness": (moderate, 94.6, "Nine columns at 20% missingness still lose only 5.4 points."),
        "severe_duplicates": (duplicates, 74.7, "89 exact repeats and ten IQR flags overlap; repeated weighting drives both."),
        "single_row": (pd.DataFrame({"x": [1]}), 82.0, "One observed value is both constant and ID-like; inference is unstable."),
        "very_wide_clean": (wide, 100.0, "Width alone is unpenalized; no implemented findings does not certify correctness."),
        "highly_sparse": (sparse, 75.7, "Ninety-percent missingness in nine columns still leaves a score in the seventies."),
        "legitimate_constant_metadata": (pd.DataFrame({"x": anchor, "source": ["test"]*100}), 92.5, "Valid metadata attracts a constant penalty without a feature-role contract."),
    }


def run():
    results = []
    for name, (frame, expected, interpretation) in cases().items():
        profile = profile_dataframe(frame)
        results.append({"case": name, "shape": list(frame.shape), "score": profile["quality_score"],
                        "expected_score": expected, "penalties": profile["score_breakdown"],
                        "issues": [{k: i[k] for k in ("issue_type", "column", "severity", "value")} for i in profile["issues"]],
                        "interpretation": interpretation, "passed": profile["quality_score"] == expected})
    return {"cases": results, "passed": all(r["passed"] for r in results)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "cases": [{k: v for k, v in c.items() if k != "issues"} for c in result["cases"]]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
