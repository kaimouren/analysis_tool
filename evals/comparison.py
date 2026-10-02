"""Authored V2 comparison scenarios; assertions target structured evidence."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from comparison import compare_datasets


def scenarios():
    def frame(values, name='value'):
        return pd.DataFrame({name: values})
    signal = frame(np.arange(100, dtype=float))
    missing = signal.copy()
    missing.loc[:29, 'value'] = np.nan
    dates = frame(pd.date_range('2024-01-01', periods=100).astype(str), 'event_date')
    malformed = dates.copy()
    malformed.loc[:39, 'event_date'] = 'not-a-date'
    multi = pd.DataFrame({name: np.arange(100, dtype=float) for name in ('a', 'b', 'c')})
    return [
        ('identical', signal, signal, set(), 'low'),
        ('row_count_drop', signal, signal.iloc[:40], {'dataset_rows'}, 'high'),
        ('missingness_spike', signal, missing, {'missingness'}, 'high'),
        ('mean_shift', signal, signal + 50, {'numeric_distribution'}, 'high'),
        ('variance_shift_same_mean', frame([-1., 1.] * 50), frame([-3., 3.] * 50), {'numeric_distribution'}, 'high'),
        ('new_category', frame(['a'] * 90 + ['b'] * 10), frame(['a'] * 90 + ['c'] * 10), {'category_membership'}, None),
        ('category_distribution_flip', frame(['desktop'] * 80 + ['mobile'] * 20), frame(['desktop'] * 20 + ['mobile'] * 80), {'categorical_distribution'}, 'high'),
        ('column_removed', multi, multi.drop(columns='c'), {'column_removed'}, 'moderate'),
        ('column_added', signal, signal.assign(new='metadata'), {'column_added'}, 'low'),
        ('numeric_to_text', signal, frame(['unknown'] * 100), {'type_change'}, None),
        ('datetime_truncated', dates, dates.iloc[:30], {'datetime_coverage', 'datetime_end_regression'}, 'high'),
        ('id_uniqueness_loss', frame([f'key-{n}' for n in range(100)]), frame([f'key-{n % 50}' for n in range(100)]), {'uniqueness'}, 'high'),
        ('small_harmless_shift', signal, signal + .01, set(), 'low'),
        ('several_moderate_shifts', multi, multi + 15, {'numeric_distribution'}, 'high'),
        ('one_severe_shift', multi, multi.assign(a=multi.a + 70), {'numeric_distribution'}, 'high'),
        ('malformed_dates', dates, malformed, {'datetime_parseability'}, 'high'),
        ('extreme_safe_numbers', frame([-1e150, 1e150] * 50), frame([-1e150, 1e150] * 50), set(), 'low'),
        ('all_null_column', frame([None] * 100), frame([None] * 100), set(), 'low'),
        ('tiny_sample', frame([1.]), frame([99.]), set(), 'low'),
        ('completely_different_schema', signal, frame(['other'] * 100, 'other'), {'no_shared_columns'}, 'not_comparable'),
        ('zero_frequency_unseen_category', frame(['old'] * 100), frame(['new'] * 100), {'categorical_distribution', 'category_membership'}, 'high'),
        ('constant_numeric_shift', frame([0.] * 100), frame([1.] * 100), {'numeric_distribution'}, 'high'),
        ('missingness_improves', missing, signal, {'missingness'}, 'high'),
        ('empty_baseline', signal.iloc[:0], signal, {'empty_dataset'}, 'not_comparable'),
    ]


def run():
    results = []
    for name, a, b, required, status in scenarios():
        started = perf_counter()
        result = compare_datasets(a, b)
        found = {f['kind'] for f in result['findings']}
        failures = []
        if required - found:
            failures.append('missing expected findings')
        if not required and found:
            failures.append('unexpected findings in negative control')
        if status and result['summary']['status'] != status:
            failures.append('unexpected summary status')
        if name == 'missingness_improves' and result['columns']['value']['missingness']['absolute_change'] != -30:
            failures.append('baseline/current reversal')
        if name == 'variance_shift_same_mean' and result['columns']['value']['numeric']['baseline']['mean'] != result['columns']['value']['numeric']['current']['mean']:
            failures.append('fixture means should be equal')
        json.dumps(result, allow_nan=False)
        for column in result['columns'].values():
            for group, metric in (('numeric', 'ks'), ('categorical', 'tvd')):
                if column[group] and column[group][metric] is not None and not 0 <= column[group][metric] <= 1:
                    failures.append('distance outside unit interval')
        results.append({"case": name, "expected_kinds": sorted(required), "observed_kinds": sorted(found),
                        "status": result['summary']['status'], "failures": failures, "passed": not failures,
                        "seconds": round(perf_counter() - started, 4)})
    return {"comparison_version": "2.0", "note": "24 constructed scenarios with authored findings/status expectations and negative controls; not a population accuracy estimate.",
            "cases": results, "passed": all(r['passed'] for r in results)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
