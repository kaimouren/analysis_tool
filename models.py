"""Typed construction boundaries; exported profiles remain ordinary JSON objects."""
from dataclasses import asdict, dataclass, field
from typing import Literal

Severity = Literal["critical", "high", "medium", "low"]
Category = Literal["validation_failure", "statistical_anomaly", "heuristic_warning"]


@dataclass(frozen=True)
class QualityIssue:
    issue_type: str
    column: str | None
    severity: Severity
    stat: str
    value: float | int
    threshold: str
    severity_rule: str
    category: Category
    confidence: str
    evidence: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.severity not in ("critical", "high", "medium", "low"):
            raise ValueError("Invalid severity.")
        if self.category not in ("validation_failure", "statistical_anomaly", "heuristic_warning"):
            raise ValueError("Invalid finding category.")
        if not self.evidence:
            raise ValueError("Every finding must include evidence.")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisMetadata:
    started_at_utc: str
    duration_seconds: float
    app_version: str
    encoding: str
