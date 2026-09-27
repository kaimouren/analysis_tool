"""Run independent expected-finding and score comparisons through CSV ingestion."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals.datasets import cases
from qa_core import load_csv, profile_dataframe


def run():
    results = []
    for name, (frame, expected, expected_score) in cases().items():
        started = perf_counter()
        loaded, _ = load_csv(frame.to_csv(index=False).encode("utf-8"), f"{name}.csv")
        profile = profile_dataframe(loaded)
        actual = {(i["issue_type"], i["column"], i["severity"]) for i in profile["issues"]}
        expected = set(expected)
        unexpected, missed = actual - expected, expected - actual
        results.append({"dataset": name, "expected_issues": sorted(expected, key=str),
                        "expected_issues_detected": len(actual & expected),
                        "unexpected_issues": sorted(unexpected, key=str), "missed_issues": sorted(missed, key=str),
                        "false_positive_count": len(unexpected), "score": profile["quality_score"],
                        "expected_score": expected_score, "runtime_seconds": round(perf_counter() - started, 6),
                        "passed": not unexpected and not missed and profile["quality_score"] == expected_score})
    return {"datasets": results, "passed": all(r["passed"] for r in results),
            "note": "False positives are mismatches against these authored synthetic expectations, not a population error-rate estimate."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["passed"] else 1)
