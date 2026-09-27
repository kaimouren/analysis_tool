"""Application orchestration; run metadata is separate from reproducible results."""
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

import pandas as pd

import qa_core
from events import emit
from ingestion import InputValidationError
from models import AnalysisMetadata
from policy import APP_VERSION


class AnalysisError(RuntimeError):
    """Safe application error with the original exception retained as its cause."""


@dataclass
class AnalysisResult:
    frame: pd.DataFrame
    profile: dict
    metadata: AnalysisMetadata


def analyze_csv(data: bytes, filename: str | None = None) -> AnalysisResult:
    started_at = datetime.now(timezone.utc).isoformat()
    started = perf_counter()
    try:
        frame, encoding = qa_core.load_csv(data, filename)
        profile = qa_core.profile_dataframe(frame)
    except InputValidationError:
        raise
    except Exception as exc:
        emit("analysis_failed", reason="unexpected")
        raise AnalysisError("Analysis could not complete. Try a smaller CSV with scalar values and report a reproducible example if this persists.") from exc
    return AnalysisResult(frame, profile, AnalysisMetadata(started_at, round(perf_counter()-started, 6), APP_VERSION, encoding))
