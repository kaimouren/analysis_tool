"""Deterministic baseline/current comparison; independent of Streamlit and I/O."""
from collections import Counter
from dataclasses import asdict
import math
import warnings

import numpy as np
import pandas as pd

from drift import COMPARISON_VERSION, DEFAULT_DRIFT_POLICY, band, change, ks_distance, numeric_stats, meets
from ingestion import InputValidationError, serialized_analysis, validate_frame
from policy import DEFAULT_THRESHOLDS


def _pct(count, total):
    return 100 * count / total if total else None


def _describe(series, policy):
    present = series.dropna()
    numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
    native_date = pd.api.types.is_datetime64_any_dtype(series)
    # Only full year-first dates; ambiguous regional formats remain unassessed.
    text = present.astype(str)
    candidates = text.where(text.str.match(r"^\d{4}-\d{2}-\d{2}(?:[ T].*)?$"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        dates = pd.to_datetime(present if native_date else candidates, errors="coerce", format="mixed", utc=True)
    numeric_count = len(present) if numeric else int(pd.to_numeric(present, errors="coerce").notna().sum()) if not native_date else 0
    date_count = int(dates.notna().sum())
    fraction = numeric_count / len(present) if len(present) else 0
    date_fraction = date_count / len(present) if len(present) else 0
    family = ('empty' if not len(present) else 'numeric' if numeric else 'datetime' if native_date or date_fraction >= policy.mostly_parseable
              else 'numeric-like text' if fraction >= policy.mostly_parseable else 'text')
    unique = int(present.nunique())
    unique_ratio = unique / len(present) if len(present) else None
    finite = [v.item() if isinstance(v, np.generic) else v for v in present if math.isfinite(v)] if numeric else []
    description = {"dtype": str(series.dtype), "family": family, "non_null_count": len(present),
                   "missing_pct": _pct(len(series) - len(present), len(series)), "unique_count": unique,
                   "uniqueness_ratio": unique_ratio, "numeric_parseable_pct": 100 * fraction if len(present) else None,
                   "datetime_parseable_pct": 100 * date_fraction if len(present) else None,
                   "infinite_count": len(present) - len(finite) if numeric else 0,
                   "positive_infinity_count": int(present.eq(np.inf).sum()) if numeric else 0,
                   "negative_infinity_count": int(present.eq(-np.inf).sum()) if numeric else 0}
    description['datetime_representation'] = (
        {"native_datetime": 1.0} if native_date and len(present) else
        {"date_only": float(text.str.fullmatch(r'\d{4}-\d{2}-\d{2}').sum()) / len(present),
         "timestamp_text": float(text.str.match(r'^\d{4}-\d{2}-\d{2}[ T]').sum()) / len(present)} if len(present) else {})
    return description, finite, dates.dropna(), present


def _category_key(value):
    # Avoid conflating the string "1" with integer 1 in mixed object data.
    if isinstance(value, (bool, np.bool_)):
        return ("boolean", str(bool(value)))
    if isinstance(value, (int, np.integer, float, np.floating)):
        return ("number", str(value))
    return ("text", str(value))


def _categorical(a, b, policy):
    left, right = Counter(map(_category_key, a)), Counter(map(_category_key, b))
    support = set(left) | set(right)
    skipped = (len(support) > policy.max_categories or
               any(len(s) >= policy.min_distribution_count and len(c) / len(s) >= DEFAULT_THRESHOLDS.id_unique_ratio
                   for s, c in ((a, left), (b, right))))
    if skipped:
        return {"status": "suppressed_high_cardinality", "tvd": None,
                "new_count": len(set(right) - set(left)), "disappeared_count": len(set(left) - set(right)),
                "top_changes": [], "new_examples": [], "disappeared_examples": []}
    def label(key):
        return {"kind": key[0], "label": key[1][:policy.category_label_chars]}
    def rates(key):
        return left[key] / len(a) if len(a) else 0, right[key] / len(b) if len(b) else 0
    ordered = sorted(support, key=lambda k: (-abs(rates(k)[1] - rates(k)[0]), k))
    top = [{**label(k), "baseline_count": left[k], "current_count": right[k],
            "baseline_pct": _pct(left[k], len(a)), "current_pct": _pct(right[k], len(b)),
            "change_pp": 100 * (rates(k)[1] - rates(k)[0]) if len(a) and len(b) else None}
           for k in ordered[:policy.display_categories]]
    return {"status": "available" if min(len(a), len(b)) >= policy.min_distribution_count else "insufficient_non_null_samples",
            "tvd": .5 * sum(abs(rates(k)[1] - rates(k)[0]) for k in sorted(support)) if len(a) and len(b) else None,
            "new_count": len(set(right) - set(left)), "disappeared_count": len(set(left) - set(right)),
            "new_examples": [label(k) for k in sorted(set(right) - set(left))[:policy.display_categories]],
            "disappeared_examples": [label(k) for k in sorted(set(left) - set(right))[:policy.display_categories]],
            "top_changes": top}


def _coverage(dates):
    ordered = sorted(set(dates.tolist()))
    if not ordered:
        return {"count": 0, "unique_timestamps": 0, "earliest": None, "latest": None, "span_days": None}, []
    return {"count": len(dates), "unique_timestamps": len(ordered), "earliest": ordered[0].isoformat(),
            "latest": ordered[-1].isoformat(), "span_days": (ordered[-1] - ordered[0]).total_seconds() / 86400}, ordered


@serialized_analysis
def compare_datasets(baseline_df, current_df, *, policy=DEFAULT_DRIFT_POLICY):
    """Return comparison schema 2.0. Empty inputs are explicit, not healthy.

    Both frames use V1 input guards. Inputs are not mutated. Values must be
    CSV-compatible scalars; unsupported structures are rejected with safe errors.
    """
    for frame in (baseline_df, current_df):
        if not isinstance(frame, pd.DataFrame):
            raise InputValidationError("Comparison requires two pandas DataFrames.")
        if not all(isinstance(name, str) and name.strip() for name in frame.columns):
            raise InputValidationError("Comparison requires nonblank string column names.")
        validate_frame(frame)
        for series in (frame[c] for c in frame.columns):
            if pd.api.types.is_complex_dtype(series) or pd.api.types.is_timedelta64_dtype(series):
                raise InputValidationError("Comparison supports real numbers, text, booleans and timestamps.")
            if pd.api.types.is_object_dtype(series):
                if any(not pd.api.types.is_scalar(v) or isinstance(v, complex) for v in series):
                    raise InputValidationError("Comparison requires scalar CSV-compatible cells.")
                for value in series:
                    if isinstance(value, (int, np.integer)) and abs(int(value)) > 1e150:
                        raise InputValidationError("Finite numeric magnitude exceeds the supported statistical range (1e150). Rescale values or inspect them separately.")
                    if isinstance(value, (float, np.floating)) and math.isfinite(value) and abs(value) > 1e150:
                        raise InputValidationError("Finite numeric magnitude exceeds the supported statistical range (1e150). Rescale values or inspect them separately.")
    names_a, names_b = set(baseline_df.columns), set(current_df.columns)
    shared = sorted(names_a & names_b)
    schema = {"added": sorted(names_b - names_a), "removed": sorted(names_a - names_b), "type_changes": []}
    findings = []

    def add(kind, column, level, evidence):
        findings.append({"kind": kind, "column": column, "severity": level, "evidence": evidence})

    for name in schema['added']:
        add('column_added', name, 'info', {"baseline_present": False, "current_present": True})
    for name in schema['removed']:
        add('column_removed', name, 'moderate', {"baseline_present": True, "current_present": False})
    if not shared and (names_a or names_b):
        add('no_shared_columns', None, 'high', {"shared_count": 0})
    for side, frame in (('baseline', baseline_df), ('current', current_df)):
        if not len(frame) or not len(frame.columns):
            add('empty_dataset', None, 'info', {"side": side, "rows": len(frame), "columns": len(frame.columns)})

    def dataset(frame):
        return {"rows": len(frame), "columns": len(frame.columns),
                "duplicate_pct": _pct(int(frame.duplicated().sum()), len(frame)) if len(frame.columns) else None,
                "missing_pct": _pct(int(frame.isna().sum().sum()), frame.size)}

    a_metrics, b_metrics = dataset(baseline_df), dataset(current_df)
    metrics = {k: change(a_metrics[k], b_metrics[k], 'percentage_points' if k.endswith('_pct') else 'count') for k in a_metrics}
    for name in ('rows', 'duplicate_pct', 'missing_pct'):
        metric = metrics[name]
        value = metric['relative_change_pct'] if name == 'rows' else metric['absolute_change']
        if value is not None:
            level = band(value, policy.rows_warn_pct if name == 'rows' else policy.rate_warn_pp,
                         policy.rows_high_pct if name == 'rows' else policy.rate_high_pp)
            if level != 'info':
                add('dataset_' + name, None, level, metric)

    columns = {}
    for name in shared:
        a, av, ad, ap = _describe(baseline_df[name], policy)
        b, bv, bd, bp = _describe(current_df[name], policy)
        entry = {"baseline": a, "current": b, "missingness": change(a['missing_pct'], b['missing_pct'], 'percentage_points'),
                 "cardinality": {"unique_count": change(a['unique_count'], b['unique_count']),
                                 "uniqueness_ratio": change(a['uniqueness_ratio'], b['uniqueness_ratio'], 'ratio')},
                 "numeric": None, "categorical": None, "datetime": None}
        columns[name] = entry
        if a['dtype'] != b['dtype'] or a['family'] != b['family']:
            risky = a['family'] != b['family'] and 'empty' not in (a['family'], b['family'])
            evidence = {"baseline_dtype": a['dtype'], "current_dtype": b['dtype'],
                        "baseline_family": a['family'], "current_family": b['family']}
            schema['type_changes'].append({"column": name, **evidence})
            add('type_change', name, 'moderate' if risky else 'info', evidence)
        missing = entry['missingness']['absolute_change']
        if missing is not None and meets(abs(missing), policy.missing_warn_pp):
            add('missingness', name, band(missing, policy.missing_warn_pp, policy.missing_high_pp), entry['missingness'])
        unique = entry['cardinality']['uniqueness_ratio']['absolute_change']
        enough = min(a['non_null_count'], b['non_null_count']) >= policy.min_distribution_count
        if enough and unique is not None and meets(abs(unique * 100), policy.unique_warn_pp):
            add('uniqueness', name, band(unique * 100, policy.unique_warn_pp, policy.unique_high_pp), entry['cardinality']['uniqueness_ratio'])
        count_change = entry['cardinality']['unique_count']['relative_change_pct']
        if enough and count_change is not None and meets(abs(count_change), policy.unique_count_warn_pct):
            add('unique_count', name, 'info', entry['cardinality']['unique_count'])
        if a['family'] == b['family'] == 'numeric':
            distance = ks_distance(av, bv)
            eligible = min(len(av), len(bv)) >= policy.min_distribution_count
            entry['numeric'] = {"baseline": numeric_stats(av), "current": numeric_stats(bv), "ks": distance,
                                "assessment": 'available' if eligible else 'insufficient_finite_samples',
                                "precision": 'Moments/quantiles use float64; extrema and KS retain integer ordering.'}
            if eligible and meets(distance, policy.ks_warn):
                add('numeric_distribution', name, band(distance, policy.ks_warn, policy.ks_high), {"ks": distance, "baseline_count": len(av), "current_count": len(bv)})
            if any(a[k] != b[k] for k in ('positive_infinity_count', 'negative_infinity_count')):
                add('non_finite_count', name, 'info',
                    {k: change(a[k], b[k]) for k in ('positive_infinity_count', 'negative_infinity_count')})
        elif a['family'] in ('text', 'numeric-like text', 'empty') and b['family'] in ('text', 'numeric-like text', 'empty'):
            cat = _categorical(ap, bp, policy)
            entry['categorical'] = cat
            if enough and cat['tvd'] is not None and meets(cat['tvd'], policy.tvd_warn):
                add('categorical_distribution', name, band(cat['tvd'], policy.tvd_warn, policy.tvd_high), {"tvd": cat['tvd'], "baseline_count": len(ap), "current_count": len(bp)})
            if cat['status'] != 'suppressed_high_cardinality' and (cat['new_count'] or cat['disappeared_count']):
                add('category_membership', name, 'info', {"new_count": cat['new_count'], "disappeared_count": cat['disappeared_count']})
        if 'datetime' in (a['family'], b['family']):
            ac, ao = _coverage(ad)
            bc, bo = _coverage(bd)
            dt = {"baseline": ac, "current": bc, "span_change": change(ac['span_days'], bc['span_days'], 'days'),
                  "end_change_days": (bo[-1] - ao[-1]).total_seconds() / 86400 if ao and bo else None,
                  "baseline_cadence_seconds": None, "current_gap_count": None}
            entry['datetime'] = dt
            if a['datetime_representation'] != b['datetime_representation']:
                add('datetime_representation', name, 'info', {"baseline": a['datetime_representation'], "current": b['datetime_representation']})
            parse_delta = change(a['datetime_parseable_pct'], b['datetime_parseable_pct'], 'percentage_points')
            if parse_delta['absolute_change'] is not None and meets(abs(parse_delta['absolute_change']), policy.missing_warn_pp):
                add('datetime_parseability', name, band(parse_delta['absolute_change'], policy.missing_warn_pp, policy.missing_high_pp), parse_delta)
            if min(len(ao), len(bo)) >= policy.min_distribution_count:
                if ac['span_days'] > 0 and bc['span_days'] / ac['span_days'] <= policy.datetime_span_ratio:
                    add('datetime_coverage', name, 'moderate', dt['span_change'])
                if dt['end_change_days'] <= -policy.datetime_end_regression_days:
                    add('datetime_end_regression', name, 'moderate', {"change_days": dt['end_change_days']})
                gaps = [(y - x).total_seconds() for x, y in zip(ao, ao[1:])]
                if gaps and min(gaps) == max(gaps) and gaps[0] > 0:
                    dt['baseline_cadence_seconds'] = gaps[0]
                    dt['current_gap_count'] = sum((y - x).total_seconds() > policy.datetime_gap_multiple * gaps[0] for x, y in zip(bo, bo[1:]))
                    if dt['current_gap_count']:
                        add('datetime_gaps', name, 'moderate', {"gap_count": dt['current_gap_count'], "baseline_cadence_seconds": gaps[0]})

    findings.sort(key=lambda f: ({'high': 0, 'moderate': 1, 'info': 2}[f['severity']], f['kind'], f['column'] or ''))
    for rank, finding in enumerate(findings, 1):
        finding.update(finding_id=f'drift-{rank:04d}', rank=rank)
    counts = {level: sum(f['severity'] == level for f in findings) for level in ('high', 'moderate', 'info')}
    evaluable = bool(shared and len(baseline_df) and len(current_df))
    status = ('not_comparable' if not evaluable else 'high' if counts['high'] or counts['moderate'] >= policy.moderate_findings_for_high
              else 'moderate' if counts['moderate'] else 'low')
    assessments = Counter()
    for col in columns.values():
        if col['numeric']:
            assessments['numeric_' + col['numeric']['assessment']] += 1
        if col['categorical']:
            assessments['categorical_' + col['categorical']['status']] += 1
    return {"comparison_version": COMPARISON_VERSION, "policy": asdict(policy),
            "summary": {"status": status, "heuristic": True, "severity_counts": counts,
                        "finding_counts": dict(sorted(Counter(f['kind'] for f in findings).items())),
                        "shared_columns": len(shared), "sampling": "none", "assessment_counts": dict(sorted(assessments.items()))},
            "schema": schema, "dataset_metrics": metrics, "columns": columns, "findings": findings}
