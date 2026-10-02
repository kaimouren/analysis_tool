"""Two-frame V2 core benchmark. Fresh process, no upload/UI/provider timing."""
import argparse
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
from comparison import compare_datasets


def measure(rows):
    rng = np.random.default_rng(23)
    baseline = pd.DataFrame({'signal': rng.normal(size=rows), 'amount': rng.uniform(1, 100, rows),
                             'category': rng.choice(['north', 'south', 'east'], rows),
                             'event_time': pd.date_range('2024-01-01', periods=rows, freq='h').astype(str)})
    current = baseline.copy()
    current['signal'] += .5
    current.loc[:rows // 10, 'amount'] = np.nan
    process = psutil.Process()
    initial = process.memory_info().rss
    peak = [initial]
    stop = threading.Event()
    def sample():
        while not stop.wait(.005):
            peak[0] = max(peak[0], process.memory_info().rss)
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    start = perf_counter()
    try:
        result = compare_datasets(baseline, current)
    finally:
        elapsed = perf_counter() - start
        peak[0] = max(peak[0], process.memory_info().rss)
        stop.set()
        sampler.join()
    return {'rows_per_frame': rows, 'columns_per_frame': 4, 'seconds': round(elapsed, 4),
            'baseline_rss_mib': round(initial / 2**20, 2), 'sampled_peak_rss_mib': round(peak[0] / 2**20, 2),
            'incremental_peak_mib': round((peak[0] - initial) / 2**20, 2), 'findings': len(result['findings'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(measure(args.worker)))
    else:
        data = {'environment': {'os': platform.system(), 'python': platform.python_version(), 'pandas': pd.__version__,
                                'numpy': np.__version__, 'logical_cpus': os.cpu_count()},
                'method': 'Fresh process per size; both input frames retained; 5ms sampled RSS; core only, no ingestion/UI/history/LLM. No sampling of input rows. Not a hosted-capacity estimate.',
                'cases': [json.loads(subprocess.check_output([sys.executable, __file__, '--worker', str(n)], text=True)) for n in (1000, 10000, 100000)]}
        if args.output:
            args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(data, indent=2))
