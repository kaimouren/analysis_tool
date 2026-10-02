"""Strict investigation contracts; no executable expressions or free-form claims."""
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class EmptyArgs(StrictModel):
    pass


class ColumnArgs(StrictModel):
    column: str = Field(min_length=1, max_length=80)


class Periods(StrictModel):
    time_column: str = Field(min_length=1, max_length=80)
    baseline_start: str = Field(min_length=10, max_length=40)
    baseline_end: str = Field(min_length=10, max_length=40)
    current_start: str = Field(min_length=10, max_length=40)
    current_end: str = Field(min_length=10, max_length=40)


class Filter(StrictModel):
    column: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=80)


class Scope(StrictModel):
    periods: Periods | None = None
    filters: list[Filter] = Field(default_factory=list, max_length=2)


class MetricArgs(Scope):
    metric_column: str = Field(min_length=1, max_length=80)
    aggregation: Literal['count', 'sum', 'mean', 'median', 'rate']


class SegmentArgs(MetricArgs):
    segment_columns: list[str] = Field(min_length=1, max_length=2)


class GroupArgs(SegmentArgs):
    left_value: str | None = Field(default=None, max_length=80)
    right_value: str | None = Field(default=None, max_length=80)

    @model_validator(mode='after')
    def contrast_pair(self):
        if (self.left_value is None) != (self.right_value is None):
            raise ValueError('Provide both contrast values.')
        if self.left_value is not None and len(self.segment_columns) != 1:
            raise ValueError('A contrast requires one segment column.')
        return self


class DistributionArgs(Scope):
    column: str = Field(min_length=1, max_length=80)
    kind: Literal['numeric', 'categorical']
    category: str | None = Field(default=None, max_length=80)


class Action(StrictModel):
    action: Literal['tool', 'finish']
    tool: str | None = Field(max_length=60)
    arguments_json: str = Field(max_length=6000)
    evidence_ids: list[str] = Field(max_length=8)
    outcome: Literal['answer', 'insufficient', 'clarify']
    # No rationale / chain-of-thought / unverified final prose field.


@dataclass(frozen=True)
class AgentLimits:
    max_steps: int = 8
    max_tool_calls: int = 8
    max_tool_errors: int = 3
    max_result_chars: int = 16000
    max_context_chars: int = 64000
    max_groups: int = 100
    top_groups: int = 10
    min_sample: int = 20
    max_seconds: int = 120

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in vars(self).values()):
            raise ValueError('Agent limits must be positive integers.')
        if self.top_groups > self.max_groups:
            raise ValueError('Top groups cannot exceed maximum groups.')


DEFAULT_AGENT_LIMITS = AgentLimits()
