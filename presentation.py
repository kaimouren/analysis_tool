"""Shared wording for computed findings; no model-generated facts."""
from qa_core import PENALTY_CAPS, SCORE_RATIONALE

SCOPE_NOTE = (
    "First-pass structural and statistical screening, not validation or modeling readiness. "
    "These checks do not establish domain correctness, semantic validity, causality, "
    "fairness, target leakage, or train/test contamination."
)
ISSUE_TITLES = {
    "missingness": "Missing values", "duplicates": "Potential duplicate rows",
    "constant": "Constant column", "near_constant": "Near-constant column",
    "possible_id": "High cardinality / possible ID-like column", "mixed_type": "Mixed semantic representations detected",
    "outliers": "IQR-flagged values", "non_finite": "Infinite numeric values",
    "empty_dataset": "Empty dataset",
    "blank_strings": "Blank or whitespace-only strings",
    "surrounding_whitespace": "Leading or trailing whitespace",
    "case_variants": "Potential casing variants",
}
ISSUE_CAVEATS = {
    "duplicates": "Exact repeated rows are not necessarily errors; no entity key or observation identity is known.",
    "outliers": "IQR flags can be common in skewed or discrete data. Zero IQR flags every value away from the shared quartile; small samples make fences unstable.",
    "possible_id": "Uniqueness alone does not identify a primary key or establish leakage. Useful products, dates, URLs, and codes can trigger this advisory flag.",
    "mixed_type": "Parser success is not semantic correctness. Codes, currencies, percentages, and placeholder strings can legitimately mix.",
    "blank_strings": "Blank strings are observed separately from pandas nulls and are not automatically replaced or scored.",
    "surrounding_whitespace": "Whitespace may be intentional; investigate before normalizing. This advisory finding has no score penalty.",
    "case_variants": "Case can carry meaning, especially in codes and languages. Case-folded matches do not prove equivalent categories; no score penalty applies.",
}


def issue_title(issue: dict) -> str:
    return ISSUE_TITLES[issue["issue_type"]]


def observation(issue: dict) -> str:
    """Render counts and denominators supplied by the profiler without inference."""
    evidence = issue.get("evidence", {})
    if "counts" in evidence:
        counts = evidence["counts"]
        return (f"Among {evidence['denominator']} non-null values: "
                f"{counts['numeric_parseable']} numeric-parseable, "
                f"{counts['date_parseable']} date-parseable, "
                f"{counts['neither_parseable']} neither. "
                f"Mixed minority share: {issue['value']:.4g}%.")
    if "count" in evidence:
        return (f"{evidence['count']} of {evidence['denominator']} "
                f"{evidence['population']} ({issue['value']:.4g}%).")
    return f"{issue['stat']} = {issue['value']}"


def penalty_rows(profile: dict) -> list[dict]:
    reasons = dict(SCORE_RATIONALE)
    thresholds = profile.get("thresholds", {})
    if thresholds:
        reasons["outliers"] = (f"15-point cap: IQR flags are not errors. Scale {thresholds['outlier_score_scale']:g}; "
                               f"scoring includes columns with outlier prevalence >= {thresholds['outlier_score_min_pct']:g}%.")
    return [{"Category": key.replace("_", " "), "Penalty": value,
             "Cap": PENALTY_CAPS.get(key, 100), "Reason for policy": reasons[key]}
            for key, value in profile["score_breakdown"].items()]
