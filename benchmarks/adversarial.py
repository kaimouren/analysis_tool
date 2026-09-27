"""Resource cases and simultaneous in-process analyses; not browser load testing."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from time import perf_counter
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import psutil
from analysis import analyze_csv
from ingestion import InputValidationError


def content(case, rows=100_000):
    if case == "too_wide":
        return (",".join(f"c{i}" for i in range(201))+"\n"+",".join("1" for _ in range(201))).encode()
    if case == "huge_cell":
        return b"text\n" + b"a"*300_000
    if case == "huge_strings":
        return pd.DataFrame({"text": ["a"*60_000+str(i) for i in range(100)]}).to_csv(index=False).encode()
    if case == "many_columns":
        return pd.DataFrame({f"c{i}": np.linspace(.01, 1.99, 100) for i in range(200)}).to_csv(index=False).encode()
    if case == "unique":
        frame = pd.DataFrame({"id": [f"event_{i:07d}" for i in range(rows)], "signal": np.linspace(.01, 1.99, rows)})
    elif case == "duplicates":
        frame = pd.DataFrame({"value": np.arange(rows)%1000, "label": ["event"]*rows})
    else:
        frame = pd.DataFrame({"id": [f"event_{i:07d}" for i in range(rows)],
                              "number": ["12", "unknown", "1,200.00", "(3.00)"]*(rows//4),
                              "date": ["2024-01-01", "bad", "2099-12-31", "2024-02-30"]*(rows//4),
                              "label": ["North", "north", " North ", " "]*(rows//4)})
    return frame.to_csv(index=False).encode()


def fingerprint(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, allow_nan=False).encode()).hexdigest()


def measure(case):
    concurrent = case.startswith("concurrency_")
    users = int(case.split("_")[-1]) if concurrent else 1
    data = content("mixed", 10_000) if concurrent else content(case, 50_000 if case == "strings" else 100_000)
    inputs = [data.replace(b"id,", f"session_{i},".encode(), 1) for i in range(users)] if concurrent else [data]
    expected = [fingerprint(analyze_csv(blob, "fixture.csv").profile) for blob in inputs] if concurrent else []
    filters_before = list(warnings.filters)
    process = psutil.Process()
    baseline = process.memory_info().rss
    peak = [baseline]
    stop = threading.Event()

    def sample():
        while not stop.wait(.005):
            peak[0] = max(peak[0], process.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    barrier = threading.Barrier(users)

    def work(index):
        barrier.wait(timeout=30)
        started = perf_counter()
        try:
            result = analyze_csv(inputs[index], "fixture.csv")
            return {"status": "accepted", "rows": len(result.frame), "issues": len(result.profile["issues"]),
                    "fingerprint": fingerprint(result.profile),
                    "own_column_only": not concurrent or result.profile["columns"][0]["column"] == f"session_{index}",
                    "seconds": round(perf_counter()-started, 4)}
        except InputValidationError as exc:
            return {"status": "rejected", "safe_reason": str(exc), "seconds": round(perf_counter()-started, 4)}

    started = perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="qa-resource-") as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                with ThreadPoolExecutor(max_workers=users) as executor:
                    results = list(executor.map(work, range(users)))
                created_files = [p.name for p in Path(directory).iterdir()]
            finally:
                os.chdir(previous)
    finally:
        elapsed = perf_counter()-started
        peak[0] = max(peak[0], process.memory_info().rss)
        stop.set()
        sampler.join()
    expected_status = "rejected" if case in ("too_wide", "huge_cell") else "accepted"
    deterministic = not concurrent or all(r.get("fingerprint") == expected[i] for i, r in enumerate(results))
    passed = all(r["status"] == expected_status and r.get("own_column_only", True) for r in results) and deterministic and not created_files and warnings.filters == filters_before
    return {"case": case, "users": users, "bytes_per_input": len(data), "wall_seconds": round(elapsed, 4),
            "baseline_rss_mib": round(baseline/2**20, 2), "sampled_peak_rss_mib": round(peak[0]/2**20, 2),
            "incremental_peak_mib": round((peak[0]-baseline)/2**20, 2), "results": results,
            "matches_sequential_profiles": deterministic if concurrent else None,
            "warning_filters_restored": warnings.filters == filters_before, "created_files": created_files,
            "provider_calls": 0, "passed": passed}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(measure(sys.argv[1])))
    else:
        names = ["too_wide", "huge_cell", "huge_strings", "many_columns", "unique", "mixed", "duplicates", "strings",
                 "concurrency_2", "concurrency_5", "concurrency_10"]
        results = [json.loads(subprocess.check_output([sys.executable, __file__, case], text=True, timeout=180)) for case in names]
        result = {"method": "Fresh subprocess per case, 5ms RSS sampling; includes ingestion/profiling, excludes input construction. Concurrent cases use threads, a start barrier, distinct 10,000-row four-column CSVs, and sequential fingerprint oracles. This does not emulate Streamlit browsers, tenant security or production load.",
                  "cases": results, "passed": all(r["passed"] for r in results)}
        (Path(__file__).parent / "adversarial-results.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"passed": result["passed"], "cases": [{k: r[k] for k in ("case", "wall_seconds", "sampled_peak_rss_mib", "passed")} for r in results]}, indent=2))
        raise SystemExit(0 if result["passed"] else 1)
