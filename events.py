"""Content-free JSON diagnostics. Unknown fields are rejected, not logged."""
import json
import logging

LOGGER = logging.getLogger("data_qa")
FIELDS = {"rows", "columns", "bytes", "duration_ms", "issue_count", "reason", "encoding"}
REASONS = {"validation", "timeout", "provider", "unexpected"}
EVENTS = {"file_loaded", "ingestion_failed", "analysis_started", "checks_completed",
          "analysis_failed", "report_generated", "llm_attempted", "llm_completed", "llm_failed"}


def emit(event: str, **fields) -> None:
    if event not in EVENTS or set(fields) - FIELDS:
        raise ValueError("Unknown diagnostic event or field.")
    for key, value in fields.items():
        if key == "reason" and value not in REASONS:
            raise ValueError("Unknown diagnostic reason.")
        if key == "encoding" and value not in ("utf-8", "utf-8-sig", "latin-1"):
            raise ValueError("Unknown diagnostic encoding.")
        if key not in ("reason", "encoding") and not isinstance(value, (int, float)):
            raise ValueError("Diagnostic measures must be numeric.")
    LOGGER.log(logging.WARNING if event.endswith("failed") else logging.INFO,
               json.dumps({"event": event, **fields}, allow_nan=False))


def configure_logging() -> None:
    """Configure only this application's logger, without changing SDK verbosity."""
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
