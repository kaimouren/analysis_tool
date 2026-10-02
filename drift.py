"""Descriptive distances and centralized, uncalibrated comparison policy."""
from dataclasses import dataclass
import math

import numpy as np


COMPARISON_VERSION = "2.0"


@dataclass(frozen=True)
class DriftPolicy:
    missing_warn_pp: float = 5
    missing_high_pp: float = 20
    rate_warn_pp: float = 5
    rate_high_pp: float = 20
    rows_warn_pct: float = 20
    rows_high_pct: float = 50
    ks_warn: float = .1
    ks_high: float = .25
    tvd_warn: float = .1
    tvd_high: float = .25
    unique_warn_pp: float = 10
    unique_high_pp: float = 30
    unique_count_warn_pct: float = 50
    min_distribution_count: int = 20
    max_categories: int = 200
    display_categories: int = 10
    category_label_chars: int = 80
    mostly_parseable: float = .8
    datetime_span_ratio: float = .5
    datetime_end_regression_days: float = 1
    datetime_gap_multiple: float = 3
    moderate_findings_for_high: int = 3

    def __post_init__(self):
        for key, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid drift policy: {key}")
        for low, high, maximum in ((self.missing_warn_pp, self.missing_high_pp, 100),
                                  (self.rate_warn_pp, self.rate_high_pp, 100),
                                  (self.unique_warn_pp, self.unique_high_pp, 100),
                                  (self.rows_warn_pct, self.rows_high_pct, float('inf')),
                                  (self.ks_warn, self.ks_high, 1), (self.tvd_warn, self.tvd_high, 1)):
            if not low < high <= maximum:
                raise ValueError("Drift bands must be increasing and in range.")
        if not .5 < self.mostly_parseable <= 1 or not 0 < self.datetime_span_ratio < 1:
            raise ValueError("Invalid parseability or coverage ratio.")
        for key in ('min_distribution_count', 'max_categories', 'display_categories',
                    'category_label_chars', 'moderate_findings_for_high'):
            if not isinstance(getattr(self, key), int):
                raise ValueError("Drift count limits must be integers.")


DEFAULT_DRIFT_POLICY = DriftPolicy()


def change(baseline, current, unit="count"):
    """Undefined baselines stay null; percent and percentage points stay distinct."""
    delta = None if baseline is None or current is None else current - baseline
    relative = None if delta is None or baseline == 0 else 100 * delta / abs(baseline)
    return {"baseline": baseline, "current": current, "absolute_change": delta,
            "relative_change_pct": relative, "unit": unit}


def band(value, warn, high):
    return "high" if abs(value) >= high else "moderate" if abs(value) >= warn else "info"


def ks_distance(baseline, current):
    """Exact empirical CDF distance. No p-value, bins, resampling or test claim.

    Python numeric ordering preserves integers beyond float64 precision, including
    comparisons between integer and float arrays. O((n+m) log(n+m)), O(n+m).
    """
    if not len(baseline) or not len(current):
        return None
    a, b = sorted(baseline), sorted(current)
    i = j = 0
    maximum = 0.0
    for value in sorted(set(a) | set(b)):
        while i < len(a) and a[i] <= value:
            i += 1
        while j < len(b) and b[j] <= value:
            j += 1
        maximum = max(maximum, abs(i / len(a) - j / len(b)))
    return maximum


def numeric_stats(values):
    """Finite-only moments use a scaled workspace; extrema retain integer values."""
    n = len(values)
    if not n:
        return {k: None for k in ('mean', 'median', 'std', 'min', 'max', 'q05', 'q25', 'q75', 'q95')} | {"count": 0}
    array = np.asarray(values, dtype=float)
    scale = float(np.max(np.abs(array))) or 1.0
    scaled = array / scale
    quantiles = np.quantile(scaled, [.05, .25, .5, .75, .95]) * scale
    return {"count": n, "mean": float(scaled.mean() * scale),
            "std": float(scaled.std(ddof=1) * scale) if n > 1 else None,
            "min": min(values), "max": max(values),
            **dict(zip(('q05', 'q25', 'median', 'q75', 'q95'), map(float, quantiles)))}
