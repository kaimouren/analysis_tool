"""V2 mathematical oracles, input boundaries and direction-sensitive evidence."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import warnings

import numpy as np
import pandas as pd
import pytest

from comparison import compare_datasets
from drift import DEFAULT_DRIFT_POLICY, change, ks_distance
from ingestion import InputValidationError


def frame(values, name='value'):
    return pd.DataFrame({name: values})


def kinds(result):
    return {f['kind'] for f in result['findings']}


def test_unchanged_is_deterministic_without_mutating_frames():
    a = pd.DataFrame({'numeric': np.linspace(0, 1, 40), 'text': ['a', 'b'] * 20})
    original = a.copy(deep=True)
    result = compare_datasets(a, a)
    assert result['summary']['status'] == 'low'
    assert result['findings'] == []
    assert result == compare_datasets(a.iloc[::-1], a)
    pd.testing.assert_frame_equal(a, original)
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('a,b,kind', [
    (pd.DataFrame({'x': [1], 'gone': [2]}), frame([1], 'x'), 'column_removed'),
    (frame([1], 'x'), pd.DataFrame({'x': [1], 'new': [2]}), 'column_added'),
    (frame(range(30)), frame(['text'] * 30), 'type_change'),
    (frame(range(30)), frame(np.arange(30, dtype=float)), 'type_change'),
])
def test_schema_direction_and_dtype(a, b, kind):
    result = compare_datasets(a, b)
    assert kind in kinds(result)
    if kind == 'column_added':
        assert result['schema']['added'] == ['new']
    if kind == 'column_removed':
        assert result['schema']['removed'] == ['gone']


@pytest.mark.parametrize('a,b', [(pd.DataFrame(), pd.DataFrame()), (frame([]), frame([1])),
                                (frame([1]), frame([])), (frame([1], 'a'), frame([1], 'b'))])
def test_empty_and_disjoint_inputs_are_not_comparable(a, b):
    result = compare_datasets(a, b)
    assert result['summary']['status'] == 'not_comparable'
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('baseline,current,delta', [([1.] * 100, [1.] * 70 + [None] * 30, 30),
    ([None] * 30 + [1.] * 70, [1.] * 100, -30), ([None] * 100, [None] * 100, 0),
    ([None] * 100, [1.] * 100, -100)])
def test_missingness_percentage_points(baseline, current, delta):
    result = compare_datasets(frame(baseline), frame(current))
    missing = result['columns']['value']['missingness']
    assert missing['absolute_change'] == delta
    assert missing['unit'] == 'percentage_points'
    assert ('missingness' in kinds(result)) == (abs(delta) >= 5)


def test_zero_denominators_and_relative_change_direction():
    assert change(0, 10)['relative_change_pct'] is None
    assert change(None, 10)['absolute_change'] is None
    assert change(100, 80)['relative_change_pct'] == -20
    result = compare_datasets(frame(range(100)), frame(range(80)))
    assert result['dataset_metrics']['rows']['absolute_change'] == -20
    assert result['dataset_metrics']['rows']['relative_change_pct'] == -20


@pytest.mark.parametrize('a,b,expected', [([0, 1], [0, 1], 0), ([0, 0], [1, 1], 1),
    ([0, 1], [1, 2], .5), ([0, 1, 2, 3], [0, 0, 2, 3], .25),
    ([2**53] * 20, [2**53+1] * 20, 1), ([], [1], None)])
def test_ks_exact_hand_calculated_oracles(a, b, expected):
    assert ks_distance(a, b) == expected
    assert ks_distance(b, a) == expected


def test_native_large_integers_do_not_collapse_in_distribution_metric():
    result = compare_datasets(frame([2**63-2] * 30), frame([2**63-1] * 30))
    numeric = result['columns']['value']['numeric']
    assert numeric['ks'] == 1
    assert numeric['current']['max'] == 2**63-1
    assert 'numeric_distribution' in kinds(result)


def test_finite_only_stats_nan_inf_and_extremes():
    a = frame([-1e150, 0., 1e150] * 10 + [np.nan, np.inf])
    b = frame([-1e150, 0., 1e150] * 10 + [np.nan, -np.inf])
    result = compare_datasets(a, b)
    numeric = result['columns']['value']['numeric']
    assert numeric['baseline']['count'] == 30
    assert numeric['baseline']['mean'] == pytest.approx(0)
    assert numeric['ks'] == 0
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('values', [[1e308], [10**300], [complex(1, 2)], [[1, 2]], [{'a': 1}]])
def test_unsupported_extreme_or_structured_values_are_safe_rejections(values):
    with pytest.raises(InputValidationError):
        compare_datasets(frame(values), frame(values))


def test_duplicate_headers_rejected():
    with pytest.raises(InputValidationError, match='unique'):
        compare_datasets(pd.DataFrame([[1, 2]], columns=['x', 'x']), frame([1]))


def test_constant_and_tiny_samples_do_not_claim_distribution_severity():
    for a, b in (([0.] * 30, [0.] * 30), ([0.], [100.]), ([np.inf] * 30, [np.inf] * 30)):
        result = compare_datasets(frame(a), frame(b))
        assert 'numeric_distribution' not in kinds(result)
        json.dumps(result, allow_nan=False)
    assert compare_datasets(frame([0.]), frame([100.]))['columns']['value']['numeric']['assessment'] == 'insufficient_finite_samples'


def test_categorical_hand_calculated_tvd_and_membership():
    result = compare_datasets(frame(['a'] * 75 + ['b'] * 25), frame(['a'] * 25 + ['c'] * 75))
    cat = result['columns']['value']['categorical']
    assert cat['tvd'] == .75
    assert cat['new_count'] == cat['disappeared_count'] == 1
    assert cat['new_examples'][0]['label'] == 'c'
    assert cat['disappeared_examples'][0]['label'] == 'b'
    assert 'categorical_distribution' in kinds(result)


def test_category_order_and_unused_pandas_categories_do_not_change_metrics():
    a = pd.Series(pd.Categorical(['a', 'b'] * 20, categories=['a', 'b', 'unused']))
    b = pd.Series(pd.Categorical(['b', 'a'] * 20, categories=['b', 'a']))
    result = compare_datasets(frame(a), frame(b))
    assert result['columns']['value']['categorical']['tvd'] == 0
    assert result['findings'] == []


def test_high_cardinality_detail_bounded_but_uniqueness_loss_detected():
    result = compare_datasets(frame([f'customer-{i}' for i in range(1000)]), frame(['customer'] * 1000))
    cat = result['columns']['value']['categorical']
    assert cat['status'] == 'suppressed_high_cardinality'
    assert cat['top_changes'] == cat['new_examples'] == []
    assert 'uniqueness' in kinds(result)


def test_mixed_objects_keep_text_distinct_from_numbers():
    a = frame(pd.Series([1, '1', False, 'false'] * 20, dtype=object))
    result = compare_datasets(a, a)
    assert result['columns']['value']['categorical']['tvd'] == 0
    assert len(result['columns']['value']['categorical']['top_changes']) == 4


def test_datetime_truncation_end_regression_and_gaps():
    dates = pd.date_range('2024-01-01', periods=100)
    truncated = compare_datasets(frame(dates), frame(dates[:30]))
    assert {'datetime_coverage', 'datetime_end_regression'} <= kinds(truncated)
    gap = compare_datasets(frame(dates), frame(dates.delete(slice(30, 50))))
    assert 'datetime_gaps' in kinds(gap)
    assert gap['columns']['value']['datetime']['current_gap_count'] == 1


def test_datetime_shift_forward_is_not_a_stale_data_claim():
    dates = pd.date_range('2024-01-01', periods=40)
    result = compare_datasets(frame(dates), frame(dates + pd.Timedelta(days=40)))
    assert not {'datetime_coverage', 'datetime_end_regression', 'datetime_gaps'} & kinds(result)
    assert result['columns']['value']['datetime']['end_change_days'] == 40


def test_malformed_dates_and_ambiguous_regional_dates_are_not_invented():
    dates = pd.date_range('2024-01-01', periods=40).astype(str).tolist()
    result = compare_datasets(frame(dates), frame(dates[:20] + ['2024-99-99'] * 20))
    assert 'datetime_parseability' in kinds(result)
    ambiguous = compare_datasets(frame(['01/02/2024'] * 40), frame(['02/01/2024'] * 40))
    assert ambiguous['columns']['value']['datetime'] is None


def test_overall_summary_rules_and_effective_policy():
    a = frame(np.arange(100, dtype=float))
    assert compare_datasets(a, a)['summary']['status'] == 'low'
    moderate = compare_datasets(a, frame(np.arange(100, dtype=float) + 15))
    assert moderate['summary']['status'] == 'moderate'
    high = compare_datasets(a, frame(np.arange(100, dtype=float) + 50))
    assert high['summary']['status'] == 'high'
    quiet = compare_datasets(a, frame(np.arange(100, dtype=float) + 15), policy=replace(DEFAULT_DRIFT_POLICY, ks_warn=.2))
    assert quiet['summary']['status'] == 'low'
    assert quiet['policy']['ks_warn'] == .2


def test_concurrent_comparisons_restore_warning_filters_and_match_sequential():
    a, b = frame(np.arange(100, dtype=float)), frame(np.arange(100, dtype=float) + 30)
    expected = compare_datasets(a, b)
    filters = list(warnings.filters)
    with ThreadPoolExecutor(max_workers=5) as pool:
        assert all(r == expected for r in pool.map(lambda _: compare_datasets(a, b), range(10)))
    assert warnings.filters == filters


@pytest.mark.parametrize('changes', [{'ks_warn': .5, 'ks_high': .2}, {'min_distribution_count': 1.5}, {'tvd_high': float('nan')}, {'mostly_parseable': .4}])
def test_invalid_threshold_policies_rejected(changes):
    with pytest.raises(ValueError):
        replace(DEFAULT_DRIFT_POLICY, **changes)
