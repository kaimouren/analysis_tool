"""Offline export-like fixtures: scenario coverage, not labeled real-world accuracy."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qa_core import load_csv, profile_dataframe

FIXTURES = Path(__file__).parent / "fixtures"
# Required observations are authored from construction. Allowed warnings are
# explicitly ambiguous: they must not be called domain errors or false positives.
SCENARIOS = {
    "crm": {
        "required": [("duplicates", None), ("missingness", "email"), ("surrounding_whitespace", "name"),
                     ("case_variants", "name"), ("mixed_type", "joined"), ("mixed_type", "customer_id")],
        "ambiguous": [("possible_id", "email")],
        "meaning": "Repeated customer export records are observable; customer identity, missing-email acceptability and ID equivalence are not established."},
    "orders": {
        "required": [("duplicates", None), ("missingness", "customer_id"), ("mixed_type", "currency_amount"),
                     ("mixed_type", "timestamp"), ("outliers", "amount")],
        "ambiguous": [],
        "meaning": "Negative amounts may be refunds; currency formatting and timezone conventions need source context."},
    "survey": {
        "required": [("duplicates", None), ("blank_strings", "comment"), ("missingness", "optional"),
                     ("surrounding_whitespace", "category"), ("case_variants", "category")],
        "ambiguous": [("constant", "cohort"), ("possible_id", "optional")],
        "meaning": "Constant cohort labels and optional missing fields can be valid; no Likert range is inferred."},
    "events": {
        "required": [("duplicates", None), ("possible_id", "event_id"), ("missingness", "property"),
                     ("mixed_type", "duration")],
        "ambiguous": [("constant", "environment"), ("constant", "property"), ("possible_id", "timestamp")],
        "meaning": "Exact repeated events and future test timestamps can be legitimate; high cardinality does not establish an invalid key."},
    "financial": {
        "required": [("missingness", "formatted"), ("mixed_type", "formatted"), ("outliers", "numeric_amount")],
        "ambiguous": [("constant", "currency"), ("possible_id", "reference")],
        "meaning": "Commas, parentheses and negative adjustments are export conventions, not automatic accounting errors."},
}


def run():
    results = []
    for name, spec in SCENARIOS.items():
        started = perf_counter()
        frame, _ = load_csv((FIXTURES / f"{name}.csv").read_bytes(), f"{name}.csv")
        profile = profile_dataframe(frame)
        actual = {(i["issue_type"], i["column"]) for i in profile["issues"]}
        required, ambiguous = set(spec["required"]), set(spec["ambiguous"])
        missed, unexpected = required - actual, actual - required - ambiguous
        results.append({"scenario": name, "required": sorted(required, key=str),
                        "expected_detections": sorted(required & actual, key=str),
                        "unexpected_detections": sorted(unexpected, key=str), "missed_detections": sorted(missed, key=str),
                        "ambiguous_warnings": sorted(actual & ambiguous, key=str),
                        "findings": [{k: i[k] for k in ("issue_type", "column", "severity", "value", "category")} for i in profile["issues"]],
                        "score": profile["quality_score"], "interpretation": spec["meaning"],
                        "runtime_seconds": round(perf_counter() - started, 6), "passed": not missed and not unexpected})
    return {"description": "Behavioral coverage using fictional local export-like fixtures; not real-world accuracy.",
            "scenarios": results, "passed": all(r["passed"] for r in results)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["passed"] else 1)
