"""Five deliberate defects in isolated copies. Never edits the working source."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ("boundary", "qa_core.py", 'value >= critical', 'value > critical', 'tests/test_v1.py::test_every_percentage_severity_boundary'),
    ("penalty", "policy.py", '"missingness": 30', '"missingness": 0', 'tests/test_qa.py::CoreTests::test_hand_calculated_statistics'),
    ("duplicates_disabled", "qa_core.py", 'duplicates = int(frame.duplicated().sum()) if c else 0', 'duplicates = 0', 'tests/test_qa.py::CoreTests::test_duplicate_denominator'),
    ("severity_swapped", "qa_core.py", 'return "high" if value >= high', 'return "low" if value >= high', 'tests/test_qa.py::CoreTests::test_semantics_and_boundaries'),
    ("report_evidence_removed", "report.py", '"Structured evidence:", "", "```json", json.dumps(issue[\'evidence\'], indent=2), "```", "",', '', 'tests/test_v1_1.py::test_export_has_structured_evidence_for_every_finding'),
]


def run():
    files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    results = []
    for name, filename, original, replacement, target in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="qa-mutation-") as directory:
            copied = Path(directory).resolve()
            for relative in files:
                source = ROOT / relative
                if source.suffix in (".py", ".csv", ".toml", ".ini"):
                    dest = copied / relative
                    assert dest.resolve().is_relative_to(copied)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
            path = copied / filename
            source = path.read_text(encoding="utf-8")
            if source.count(original) != 1:
                raise RuntimeError(f"Mutation anchor must match once: {name}")
            path.write_text(source.replace(original, replacement, 1), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "pytest", "-q", target], cwd=copied, capture_output=True, text=True, timeout=120)
            # Collection/import crashes are not a successful mutation kill.
            killed = result.returncode == 1 and "AssertionError" in result.stdout and "failed" in result.stdout
            results.append({"mutation": name, "target_test": target, "exit_code": result.returncode,
                            "killed_by_assertion": killed,
                            "summary": next((line for line in reversed(result.stdout.splitlines()) if "failed" in line), "No assertion summary")})
    return {"mutations": results, "passed": all(r["killed_by_assertion"] for r in results)}


if __name__ == "__main__":
    result = run()
    (ROOT / "evals/mutation-results.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
