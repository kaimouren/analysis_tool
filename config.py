"""Configuration precedence and resource limits, independent of the UI."""
import os
from collections.abc import Mapping
from urllib.parse import urlsplit

MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
DEFAULT_MODEL = "gpt-4o-mini"


def resolve_setting(name: str, explicit: str = "", *,
                    secrets: Mapping | None = None, default: str = "") -> str:
    """Resolve a nonblank sidebar value, environment, then optional secrets."""
    for value in (explicit, os.getenv(name, "")):
        if value.strip():
            return value.strip()
    if secrets is not None:
        try:
            value = secrets.get(name, "")
        except (FileNotFoundError, KeyError):
            value = ""
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def validate_upload_size(size: int) -> None:
    """Reject oversized CSVs before decoding and allocating a DataFrame."""
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(f"CSV exceeds the {MAX_UPLOAD_MB} MiB upload limit. Use a smaller file; profiling runs in memory.")


def user_endpoint_allowed(endpoint: str, configured_endpoint: str = "") -> bool:
    """Only exact administrator-approved endpoints may be selected by a browser."""
    approved = {"https://api.openai.com/v1", configured_endpoint.rstrip("/")}
    approved.update(value.strip().rstrip("/") for value in os.getenv("QA_ALLOWED_LLM_BASE_URLS", "").split(",") if value.strip())
    try:
        parsed = urlsplit(endpoint)
        return bool(parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username
                    and not parsed.password and not parsed.query and not parsed.fragment
                    and endpoint.rstrip("/") in approved)
    except ValueError:
        return False
