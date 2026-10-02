"""Versioned heuristic policy. Overrides are explicit, never model-controlled."""
from dataclasses import asdict, dataclass, field
import math

APP_VERSION = "2.1.0"
PROFILE_VERSION = "1.4"
SCORE_POLICY_VERSION = "1.0"
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PENALTY_CAPS = {"missingness": 30, "duplicates": 20, "outliers": 15,
                "constant": 15, "near_constant": 5, "possible_id": 3,
                "mixed_type": 12, "non_finite": 10}


@dataclass(frozen=True)
class SeverityBands:
    medium: float
    high: float
    critical: float | None = None

    def __post_init__(self):
        values = [self.medium, self.high] + ([] if self.critical is None else [self.critical])
        if any(not math.isfinite(v) or not 0 <= v <= 100 for v in values) or values != sorted(set(values)):
            raise ValueError("Severity bands must be finite, increasing percentages between 0 and 100.")


@dataclass(frozen=True)
class QualityThresholds:
    missingness: SeverityBands = field(default_factory=lambda: SeverityBands(5, 20, 50))
    duplicates: SeverityBands = field(default_factory=lambda: SeverityBands(2, 10, 30))
    outliers: SeverityBands = field(default_factory=lambda: SeverityBands(1, 10))
    mixed_type: SeverityBands = field(default_factory=lambda: SeverityBands(0, 10))
    near_constant_ratio: float = .95
    id_unique_ratio: float = .95
    datetime_ratio: float = .95
    long_text_length: int = 80
    iqr_multiplier: float = 1.5
    outlier_score_min_pct: float = 1
    outlier_score_scale: float = 5
    small_sample_rows: int = 20
    sequence_min_unique: int = 20
    top_values_limit: int = 15
    example_limit: int = 3
    example_chars: int = 80

    def __post_init__(self):
        for name in ("near_constant_ratio", "id_unique_ratio", "datetime_ratio"):
            if not 0 < getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in (0, 1].")
        for name in ("long_text_length", "small_sample_rows", "sequence_min_unique", "top_values_limit", "example_limit", "example_chars"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        for name in ("iqr_multiplier", "outlier_score_scale"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive and finite.")
        if not 0 <= self.outlier_score_min_pct <= 100:
            raise ValueError("outlier_score_min_pct must be in [0, 100].")

    def bands(self, kind: str) -> dict:
        return asdict(getattr(self, kind))


DEFAULT_THRESHOLDS = QualityThresholds()
SEVERITY_THRESHOLDS = {kind: {k: v for k, v in DEFAULT_THRESHOLDS.bands(kind).items() if v is not None}
                       for kind in ("missingness", "duplicates", "outliers", "mixed_type")}
