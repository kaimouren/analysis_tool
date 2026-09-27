"""Measure full-frame profiling in a fresh process per size; no LLM or UI timing."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import psutil
from ingestion import InputLimits
from qa_core import profile_dataframe


def measure(rows):
    rng = np.random.default_rng(42)
    frame = pd.DataFrame({"signal": rng.normal(size=rows), "amount": rng.lognormal(size=rows),
                          "age_like": rng.integers(18, 90, rows), "sequence": np.arange(rows),
                          "region": rng.choice(["North", "South", " East "], rows),
                          "mixed": rng.choice(["12", "24", "unknown"], rows),
                          "partial": np.where(rng.random(rows) < .2, np.nan, rng.normal(size=rows)),
                          "date": rng.choice(["2024-01-01", "2024-02-01", "unknown"], rows)})
    process = psutil.Process()
    baseline = process.memory_info().rss
    peak = [baseline]
    stop = threading.Event()

    def sample():
        while not stop.wait(.005):
            peak[0] = max(peak[0], process.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    started = perf_counter()
    try:
        profile = profile_dataframe(frame, limits=InputLimits(max_rows=max(200_000, rows), max_cells=max(2_000_000, rows * 8)))
    finally:
        elapsed = perf_counter() - started
        peak[0] = max(peak[0], process.memory_info().rss)
        stop.set()
        sampler.join()
    return {"rows": rows, "columns": 8, "runtime_seconds": round(elapsed, 4),
            "baseline_rss_mib": round(baseline / 2**20, 2), "sampled_peak_rss_mib": round(peak[0] / 2**20, 2),
            "incremental_peak_mib": round((peak[0] - baseline) / 2**20, 2), "issues": len(profile["issues"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", nargs="+", type=int, default=[500, 10_000, 100_000])
    parser.add_argument("--worker", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        print(json.dumps(measure(args.worker)))
    else:
        results = [json.loads(subprocess.check_output([sys.executable, __file__, "--worker", str(n)], text=True)) for n in args.rows]
        result = {"measured_utc": datetime.now(timezone.utc).isoformat(),
                  "environment": {"os": platform.system(), "release": platform.release(), "python": platform.python_version(),
                                  "logical_cpus": os.cpu_count(), "pandas": pd.__version__, "numpy": np.__version__},
                  "method": "One fresh process per size, fixed seed, 8 columns, input generation excluded; RSS sampled every 5 ms. Above default limits, only this benchmark explicitly raises row/cell guards. No ingestion, UI, concurrent sessions, report, or LLM timing.",
                  "results": results}
        rendered = json.dumps(result, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
