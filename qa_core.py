"""Pure, deterministic CSV profiling. No UI, network, or model dependencies."""
from dataclasses import asdict
from copy import deepcopy
from time import perf_counter
import re
import warnings

import numpy as np
import pandas as pd
from ingestion import DEFAULT_LIMITS, InputLimits, PARSER_LOCK, load_csv as load_csv, serialized_analysis, validate_frame
from events import emit
from models import QualityIssue
from policy import (DEFAULT_THRESHOLDS, QualityThresholds, PENALTY_CAPS,
                    SEVERITY_ORDER, PROFILE_VERSION, SCORE_POLICY_VERSION,
                    SEVERITY_THRESHOLDS as SEVERITY_THRESHOLDS)


SCORE_RATIONALE = {
    "missingness": "30-point cap: coverage gets the largest weight; missingness is not automatically harmful.",
    "duplicates": "20-point cap: repeated observations may distort weighting or splits, but can be valid.",
    "outliers": "15-point cap: finite-value prevalence matters; IQR flags are not errors. Scales to the cap at pooled prevalence of 20%.",
    "constant": "15-point cap: no observed variation; averaged over columns rather than assuming feature importance.",
    "near_constant": "5-point cap: a weaker signal than constant; rare values may be informative.",
    "possible_id": "3-point cap: weak advisory signal; uniqueness does not establish an identifier or leakage.",
    "mixed_type": "12-point cap: conversion inconsistencies deserve review; legitimate codes can also trigger.",
    "non_finite": "10-point cap: infinities can break estimators; the observed cell fraction controls impact.",
    "empty_dataset": "100-point penalty: no observations or columns to assess.",
}


def string_quality(present: pd.Series) -> dict:
    """Flag observable formatting differences without normalizing source values."""
    text = present.astype(str)
    stripped = text.str.strip()
    blank = stripped.eq("")
    whitespace = text.ne(stripped) & ~blank
    nonblank = stripped[~blank]
    folded = nonblank.str.casefold()
    variant_counts = nonblank.groupby(folded).transform("nunique")
    return {"blank_strings": int(blank.sum()), "surrounding_whitespace": int(whitespace.sum()),
            "case_variants": int(variant_counts.gt(1).sum())}


def semantic_evidence(present, numeric, dates, policy=DEFAULT_THRESHOLDS) -> dict:
    """Describe parser behavior without claiming the intended meaning of values."""
    text = present.astype(str).str.strip()
    numeric_mask = numeric.notna()
    groups = {"numeric_parseable": numeric_mask, "date_parseable": dates & ~numeric_mask,
              "neither_parseable": ~(numeric_mask | dates)}
    return {
        "non_null_count": len(present),
        "counts": {label: int(mask.sum()) for label, mask in groups.items()},
        "examples": {label: text[mask].drop_duplicates().head(policy.example_limit).str.slice(0, policy.example_chars).tolist()
                     for label, mask in groups.items()},
        "leading_zero_integer_count": int(text.str.fullmatch(r"[+-]?0\d+").sum()),
        "currency_like_count": int(text.str.contains(r"[$€£¥]").sum()),
        "percentage_like_count": int(text.str.endswith("%").sum()),
    }


def severity_rule(kind: str, level: str, policy=DEFAULT_THRESHOLDS) -> str:
    """Use the same boundaries for badge assignment and its explanation."""
    if kind in SEVERITY_THRESHOLDS:
        thresholds = {k: v for k, v in policy.bands(kind).items() if v is not None}
        ordered = [(name, thresholds[name]) for name in ("critical", "high", "medium") if name in thresholds]
        if level == "low":
            return f"Detected percentage > 0% and < {ordered[-1][1]}% → low."
        index = next(i for i, item in enumerate(ordered) if item[0] == level)
        lower = ordered[index][1]
        upper = f" and < {ordered[index-1][1]}%" if index else ""
        comparison = "> 0%" if lower == 0 else f">= {lower}%"
        return f"Detected percentage {comparison}{upper} → {level}."
    return {"constant": "One unique non-null value → high.",
            "near_constant": f"Top non-null value >= {policy.near_constant_ratio*100:g}%, excluding constants → medium.",
            "possible_id": f"Unique ratio >= {policy.id_unique_ratio:g} with eligible dtype and length → low advisory finding.",
            "non_finite": "Any infinite numeric values → high.",
            "blank_strings": "Any observed blank strings → low advisory finding; no automatic missing-value conversion.",
            "surrounding_whitespace": "Any nonblank values with surrounding whitespace → low advisory finding.",
            "case_variants": "Any nonblank case-folded group with distinct spellings → low advisory finding.",
            "empty_dataset": "No rows or no columns → critical."}[kind]


def ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else 0.0


def scalar(value):
    if pd.isna(value):
        return None
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else str(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    return str(value)


def date_mask(values):
    # Exclude bare numbers: pandas otherwise interprets IDs as epoch timestamps.
    text = values.astype(str).str.strip()
    # Require an explicit year so incomplete dates cannot depend on today's date.
    candidates = text.where(~text.str.fullmatch(r"[+-]?\d+(\.\d+)?") & text.str.contains(r"\b\d{4}\b"))
    with PARSER_LOCK, warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.to_datetime(candidates, errors="coerce", format="mixed", utc=True).notna()


def profile_column(series: pd.Series, policy: QualityThresholds = DEFAULT_THRESHOLDS) -> dict:
    """Describe observed values and compute inputs for deterministic rules."""
    present = series.dropna()
    n, count = len(series), len(present)
    unique = int(present.nunique())
    counts = present.value_counts()
    top_count = int(counts.iloc[0]) if count else 0
    text_kind = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    numeric_kind = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
    numeric = pd.to_numeric(present, errors="coerce")
    finite = numeric[np.isfinite(numeric)].astype(float)
    numeric_count = int(numeric.notna().sum())
    numeric_fraction = ratio(numeric_count, count)
    dates = date_mask(present) if text_kind else pd.Series(False, index=present.index)
    if pd.api.types.is_datetime64_any_dtype(series):
        dates = present.notna()
    parsed_dates = int(dates.sum())
    date_fraction = ratio(parsed_dates, count)
    long_text = bool(count and text_kind and present.astype(str).str.len().median() > policy.long_text_length)
    integer_like = bool(numeric_kind and len(finite) == count and count and (finite % 1 == 0).all())
    mixed_numeric = bool(text_kind and 0 < numeric_fraction < 1)
    mixed_dates = bool(text_kind and 0 < date_fraction < 1)
    evidence = semantic_evidence(present, numeric, dates, policy) if text_kind else None
    semantic = "empty" if not count else "categorical"
    if not count:
        semantic = "empty"
    elif pd.api.types.is_bool_dtype(series):
        semantic = "boolean"
    elif long_text:
        semantic = "long text"
    elif numeric_kind:
        semantic = "numeric"
    elif pd.api.types.is_datetime64_any_dtype(series):
        semantic = "datetime-like"
    elif numeric_fraction == 1:
        semantic = "identifier-like text" if evidence and evidence["leading_zero_integer_count"] else "numeric-like text"
    elif date_fraction >= policy.datetime_ratio:
        semantic = "datetime-like"
    elif mixed_numeric or mixed_dates:
        semantic = "mixed"
    constant = unique == 1
    near_constant = bool(count and not constant and top_count / count >= policy.near_constant_ratio)
    possible_id = bool(count and unique / count >= policy.id_unique_ratio and (text_kind or integer_like) and not long_text)
    name_hint = bool(re.search(r"(?:^|[_\W])(?:id|uuid|key)(?:$|[_\W])", str(series.name).lower()))
    unit_step_sequence = False
    if integer_like and unique >= policy.sequence_min_unique:
        ordered_values = numeric.drop_duplicates().sort_values()
        unit_step_sequence = bool(ordered_values.diff().dropna().eq(1).all())
    result = {"column": str(series.name), "dtype": str(series.dtype), "semantic_type": semantic,
              "missing_count": n-count, "missing_pct": 100*ratio(n-count, n),
              "non_null_count": count, "unique_count": unique, "unique_ratio": ratio(unique, count),
              "most_frequent_value": scalar(counts.index[0]) if count else None,
              "most_frequent_count": top_count, "most_frequent_pct": 100*ratio(top_count, count),
              "top_values": [{"value": scalar(value), "count": int(frequency)}
                             for value, frequency in counts.head(policy.top_values_limit).items()],
              "constant": constant, "near_constant": near_constant, "possible_id": possible_id,
              "id_evidence": {"name_hint": name_hint, "unit_step_integer_sequence": unit_step_sequence,
                              "median_text_length": float(present.astype(str).str.len().median()) if count and text_kind else None,
                              "role_established": False},
              "semantic_evidence": evidence,
              "string_quality": string_quality(present) if text_kind else {},
              "datetime_parseability_pct": 100*date_fraction,
              "mixed_type": mixed_numeric or mixed_dates,
              "numeric_parseability_pct": 100*numeric_fraction,
              "mixed_minority_pct": 100*ratio(max(min(numeric_count, count-numeric_count) if mixed_numeric else 0,
                                                   min(parsed_dates, count-parsed_dates) if mixed_dates else 0), count),
              "numeric_stats": {}, "outlier_count": 0, "outlier_pct": 0.0,
              "outlier_lower": None, "outlier_upper": None, "finite_count": int(len(finite)),
              "non_finite_count": int((numeric.notna() & ~np.isfinite(numeric)).sum())}
    if numeric_kind and len(finite):
        result["numeric_stats"] = {key: scalar(val) for key, val in finite.describe().items()}
        # Integer extrema should not be rounded by the float statistical workspace.
        original_finite = numeric[np.isfinite(numeric)]
        result["numeric_stats"].update(min=scalar(original_finite.min()), max=scalar(original_finite.max()))
        result["numeric_precision_note"] = (
            "Integer magnitude exceeds exact float64 integer precision. Extrema, uniqueness and duplicate counts retain parsed integer values; means, quantiles and IQR flags are approximate."
            if pd.api.types.is_integer_dtype(series) and (original_finite.gt(2**53) | original_finite.lt(-(2**53))).any() else None)
        q1, q3 = finite.quantile([.25, .75])
        lower, upper = q1 - policy.iqr_multiplier*(q3-q1), q3 + policy.iqr_multiplier*(q3-q1)
        outliers = int(((finite < lower) | (finite > upper)).sum())
        result.update(outlier_count=outliers, outlier_pct=100*ratio(outliers, len(finite)),
                      outlier_lower=scalar(lower), outlier_upper=scalar(upper))
    return result


def severity(value, high, medium, critical=None):
    if critical is not None and value >= critical:
        return "critical"
    return "high" if value >= high else "medium" if value >= medium else "low"


def detect_issues(summary, columns, policy=DEFAULT_THRESHOLDS):
    issues = []

    def add(kind, column, level, stat, value, threshold, evidence=None):
        category = "validation_failure" if kind == "empty_dataset" else "statistical_anomaly" if kind == "outliers" else "heuristic_warning"
        confidence = "Exact observation; semantic impact unverified."
        if kind in ("possible_id", "mixed_type", "case_variants"):
            confidence = "Heuristic interpretation; underlying counts are exact under the documented parser/rule."
        issue = QualityIssue(kind, column, level, stat, value, threshold, severity_rule(kind, level, policy),
                             category, confidence, evidence or {"stat": stat, "observed": value})
        issues.append(issue.to_dict())

    if not summary["rows"] or not summary["columns"]:
        add("empty_dataset", None, "critical", "rows", summary["rows"], "rows and columns must be > 0")
    if summary["duplicate_rows"]:
        value = summary["duplicate_pct"]
        add("duplicates", None, severity(value, **policy.bands("duplicates")), "duplicate_pct", value, "> 0%",
            {"count": summary["duplicate_rows"], "denominator": summary["rows"], "population": "rows after the first exact occurrence"})
    for col in columns:
        name = col["column"]
        if col["missing_count"]:
            value = col["missing_pct"]
            add("missingness", name, severity(value, **policy.bands("missingness")), "missing_pct", value, "> 0%",
                {"count": col["missing_count"], "denominator": summary["rows"], "population": "rows with a missing value"})
        for flag, level, stat, threshold in (
            ("constant", "high", "unique_count", "= 1 non-null unique value"),
            ("near_constant", "medium", "most_frequent_pct", f">= {policy.near_constant_ratio*100:g}% of non-null rows; not constant"),
            ("possible_id", "low", "unique_ratio", f">= {policy.id_unique_ratio:g}; string/object or integer-like; not long text"),
        ):
            if col[flag]:
                add(flag, name, level, stat, col[stat], threshold,
                    {"non_null_count": col["non_null_count"], "unique_count": col["unique_count"], "most_frequent_count": col["most_frequent_count"]})
        if col["mixed_type"]:
            value = col["mixed_minority_pct"]
            add("mixed_type", name, severity(value, **policy.bands("mixed_type")), "mixed_minority_pct", value, "> 0%; numeric or date mixture",
                {"counts": col["semantic_evidence"]["counts"], "denominator": col["non_null_count"]})
        if col["outlier_count"]:
            value = col["outlier_pct"]
            add("outliers", name, severity(value, **policy.bands("outliers")), "outlier_pct", value, f"> 0%; outside Q1 - {policy.iqr_multiplier:g} IQR or Q3 + {policy.iqr_multiplier:g} IQR",
                {"count": col["outlier_count"], "denominator": col["finite_count"], "population": "finite numeric values outside the IQR fences",
                 "lower": col["outlier_lower"], "upper": col["outlier_upper"]})
        if col["non_finite_count"]:
            add("non_finite", name, "high", "non_finite_count", col["non_finite_count"], "> 0")
        for kind, count in col["string_quality"].items():
            if count:
                add(kind, name, "low", "affected_non_null_pct", 100*ratio(count, col["non_null_count"]), "> 0%; advisory text-format observation",
                    {"count": count, "denominator": col["non_null_count"], "population": "non-null values affected", "scored": False})
    # Severity first, then stable type/name ordering; never let a model rank issues.
    issues.sort(key=lambda x: (SEVERITY_ORDER[x["severity"]], x["issue_type"], x["column"] or ""))
    for index, issue in enumerate(issues):
        issue["issue_id"] = f"issue_{index+1}"
        issue["rank"] = index+1
    return issues


def score_dataset(summary, columns, policy=DEFAULT_THRESHOLDS):
    c = len(columns)
    # Category caps keep a wide dataset or many IDs from dominating the score.
    severe_outliers = sum(p["outlier_count"] for p in columns if p["outlier_pct"] >= policy.outlier_score_min_pct)
    numeric_total = sum(p["finite_count"] for p in columns if p["numeric_stats"])
    fractions = {
        "missingness": summary["missing_pct"] / 100,
        "duplicates": summary["duplicate_pct"] / 100,
        "outliers": min(1.0, policy.outlier_score_scale*ratio(severe_outliers, numeric_total)),
        **{key: ratio(sum(p[key] for p in columns), c)
           for key in ("constant", "near_constant", "possible_id", "mixed_type")},
        "non_finite": ratio(sum(p["non_finite_count"] for p in columns), summary["rows"]*c),
    }
    penalties = {key: round(cap*fractions[key], 6) for key, cap in PENALTY_CAPS.items()}
    if not summary["rows"] or not c:
        penalties["empty_dataset"] = 100.0
    return round(max(0.0, 100-sum(penalties.values())), 2), penalties


@serialized_analysis
def profile_dataframe(frame: pd.DataFrame, *, thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
                      limits: InputLimits = DEFAULT_LIMITS) -> dict:
    """Profile without modifying frame. All returned values are JSON serializable."""
    started = perf_counter()
    validate_frame(frame, limits)
    emit("analysis_started", rows=len(frame), columns=len(frame.columns))
    n, c = frame.shape
    duplicates = int(frame.duplicated().sum()) if c else 0
    summary = {"rows": n, "columns": c, "missing_cells": int(frame.isna().sum().sum()),
               "missing_pct": 100*ratio(int(frame.isna().sum().sum()), n*c),
               "duplicate_rows": duplicates, "duplicate_pct": 100*ratio(duplicates, n)}
    columns = [profile_column(frame[col], thresholds) for col in frame.columns]
    raw_samples = frame.attrs.get("qa_raw_samples", {})
    for column in columns:
        sample = raw_samples.get(column["column"])
        column["raw_representation"] = deepcopy(sample) if sample and (sample["risks"] or column["mixed_type"]) else None
    score, penalties = score_dataset(summary, columns, thresholds)
    issues = detect_issues(summary, columns, thresholds)
    summary["severity_counts"] = {level: sum(issue["severity"] == level for issue in issues) for level in SEVERITY_ORDER}
    worst_missing = max(columns, key=lambda p: p["missing_pct"], default=None)
    summary.update(max_column_missing_pct=worst_missing["missing_pct"] if worst_missing else 0,
                   max_missing_column=worst_missing["column"] if worst_missing and worst_missing["missing_count"] else None)
    if not n or not c:
        review = "No observations to assess"
    elif issues:
        review = f"{issues[0]['severity'].capitalize()}-severity findings detected — review required"
    else:
        review = "No findings under the implemented rules"
    notes = []
    if any(col.get("numeric_precision_note") for col in columns):
        notes.append("Some parsed integers exceed exact float64 integer precision. Review column precision notes; aggregate statistics and IQR flags use approximate floating-point arithmetic.")
    if 0 < n < thresholds.small_sample_rows:
        notes.append(f"Fewer than {thresholds.small_sample_rows} rows: concentration, uniqueness, and IQR flags describe this small sample only; they do not establish population properties.")
    emit("checks_completed", issue_count=len(issues), duration_ms=round((perf_counter()-started)*1000, 3))
    return {"summary": summary, "columns": columns, "issues": issues,
            "thresholds": asdict(thresholds),
            "review_status": review, "context_notes": notes,
            "quality_score": score, "score_breakdown": penalties,
            "profile_version": PROFILE_VERSION, "score_policy_version": SCORE_POLICY_VERSION}
