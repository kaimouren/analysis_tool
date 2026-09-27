"""Bounded comma-delimited CSV ingestion. No uploads are persisted."""
import csv
from dataclasses import dataclass
from functools import wraps
from io import StringIO
from pathlib import Path
import re
import threading
import warnings

import pandas as pd

from config import validate_upload_size
from events import emit

# Python 3.11 warning filters are process-global, including contexts inside
# pandas/NumPy operations. Serialize complete public analysis entry points.
PARSER_LOCK = threading.RLock()


def serialized_analysis(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with PARSER_LOCK:
            return function(*args, **kwargs)
    return wrapped


class InputValidationError(ValueError):
    """An expected input failure whose message is safe to display."""


@dataclass(frozen=True)
class InputLimits:
    max_rows: int = 200_000
    max_columns: int = 200
    max_cells: int = 2_000_000
    max_frame_bytes: int = 256 * 1024 * 1024
    max_cell_chars: int = 65_536

    def __post_init__(self):
        if any(not isinstance(v, int) or v < 1 for v in vars(self).values()):
            raise ValueError("Input limits must be positive integers.")


DEFAULT_LIMITS = InputLimits()
RAW_SAMPLE_ROWS = 100
RAW_SAMPLE_VALUES = 3
RAW_SAMPLE_CHARS = 80


def representation_risks(token: str) -> list[str]:
    """Explain lexical ambiguity, without coercing tokens or asserting errors."""
    text = token.strip()
    risks = []
    if re.fullmatch(r"[+-]?0\d+", text):
        risks.append("leading-zero numeric token")
    if re.fullmatch(r"[+-]?\d{16,}", text):
        risks.append("large integer token; numeric precision may differ")
    if text.casefold() in {"na", "n/a", "nan", "null", "none", "<na>", "#n/a"}:
        risks.append("NA-like token may become missing")
    if any(char in text for char in "$€£¥") or text.endswith("%"):
        risks.append("currency/percentage representation may remain text")
    if re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}", text):
        risks.append("date-like token; ordering may be ambiguous")
    return risks


def validate_frame(frame: pd.DataFrame, limits: InputLimits = DEFAULT_LIMITS) -> None:
    rows, columns = frame.shape
    if columns > limits.max_columns or rows > limits.max_rows or rows * columns > limits.max_cells:
        raise InputValidationError(f"Dataset exceeds the analysis limit ({limits.max_rows:,} rows, {limits.max_columns} columns, {limits.max_cells:,} cells). Select fewer rows or columns.")
    if not frame.columns.is_unique or len(set(map(str, frame.columns))) != columns:
        raise InputValidationError("Column names must be unique. Rename duplicate headers and retry.")
    if int(frame.memory_usage(index=True, deep=True).sum()) > limits.max_frame_bytes:
        raise InputValidationError("Decoded dataset exceeds the memory budget. Use fewer rows or columns.")
    for name in frame.columns:
        series = frame[name]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            lengths = series.astype("string").str.len()
            if lengths.gt(limits.max_cell_chars).any():
                raise InputValidationError(f"A text cell exceeds {limits.max_cell_chars:,} characters. Shorten large text fields before analysis.")
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            finite = series.dropna()
            # Infinities have a dedicated QA finding; finite values outside this
            # conservative range can overflow variance/fence calculations.
            extreme = (finite.gt(1e150) | finite.lt(-1e150)) & ~finite.isin([float("inf"), -float("inf")])
            if extreme.any():
                raise InputValidationError("Finite numeric magnitude exceeds the supported statistical range (1e150). Rescale values or inspect them separately.")


@serialized_analysis
def load_csv(data: bytes, filename: str | None = None, *, limits: InputLimits = DEFAULT_LIMITS) -> tuple[pd.DataFrame, str]:
    """Validate file/header boundaries before pandas can normalize them."""
    try:
        try:
            validate_upload_size(len(data))
        except ValueError as exc:
            raise InputValidationError("CSV exceeds the 10 MiB upload limit. Select a smaller file.") from exc
        if filename and Path(filename).suffix.lower() != ".csv":
            raise InputValidationError("Unsupported file type. Export a comma-delimited .csv file and retry.")
        if not data.strip():
            raise InputValidationError("CSV is empty. Provide a header and at least one data row.")
        if re.search(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", data):
            raise InputValidationError("Input contains binary/control bytes or an unsupported encoding. Export plain UTF-8 CSV and retry.")
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                decoded = data.decode(encoding).lstrip("\ufeff")
                break
            except UnicodeDecodeError:
                continue
        else:
            raise InputValidationError("Could not decode input. Export UTF-8 CSV and retry.")
        reader = csv.reader(StringIO(decoded), strict=True)
        header = next((row for row in reader if row), [])
        if not header or any(not name.strip() for name in header):
            raise InputValidationError("CSV needs nonblank column headers. Name each column and retry.")
        if len(set(header)) != len(header):
            raise InputValidationError("CSV contains duplicate column names. Rename duplicate headers and retry.")
        if len(header) > limits.max_columns:
            raise InputValidationError(f"CSV has too many columns (limit {limits.max_columns}). Select fewer columns.")
        if any(len(value) > limits.max_cell_chars for value in header):
            raise InputValidationError("A header is too long. Shorten column names and retry.")
        # Stream one logical record at a time; embedded newlines and quoted commas
        # stay valid. Do not retain a second complete table or change csv globals.
        samples = {name: {"first": [], "suspicious": [], "risks": []} for name in header}
        for row_index, row in enumerate(reader):
            if any(len(value) > limits.max_cell_chars for value in row):
                raise InputValidationError(f"A text cell exceeds {limits.max_cell_chars:,} characters. Shorten large text fields before analysis.")
            if row_index < RAW_SAMPLE_ROWS:
                for name, value in zip(header, row):
                    if not value:
                        continue
                    entry = samples[name]
                    token = value[:RAW_SAMPLE_CHARS]
                    risks = representation_risks(value)
                    for risk in risks:
                        if risk not in entry["risks"]:
                            entry["risks"].append(risk)
                    bucket = entry["suspicious"] if risks else entry["first"]
                    if token not in bucket and len(bucket) < RAW_SAMPLE_VALUES:
                        bucket.append(token)
        row_limit = min(limits.max_rows, limits.max_cells // len(header))
        with PARSER_LOCK, warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            frame = pd.read_csv(StringIO(decoded), on_bad_lines="error", index_col=False, nrows=row_limit + 1)
        validate_frame(frame, limits)
        frame.attrs["qa_raw_samples"] = {
            name: {"examples": list(dict.fromkeys(entry["suspicious"] + entry["first"]))[:RAW_SAMPLE_VALUES],
                   "risks": entry["risks"], "record_limit": RAW_SAMPLE_ROWS, "character_limit": RAW_SAMPLE_CHARS,
                   "note": "Decoded CSV fields before pandas inference; quoting/BOM removed, examples truncated. Early-record samples, not row-aligned or lossless source bytes."}
            for name, entry in samples.items() if entry["suspicious"] or entry["first"]}
        emit("file_loaded", rows=len(frame), columns=len(frame.columns), bytes=len(data), encoding=encoding)
        return frame, encoding
    except (pd.errors.ParserError, pd.errors.ParserWarning, pd.errors.EmptyDataError, csv.Error) as exc:
        emit("ingestion_failed", reason="validation")
        raise InputValidationError("Could not parse CSV. Check commas, quotes, header width and oversized text fields, then export again.") from exc
    except ValueError as exc:
        emit("ingestion_failed", reason="validation")
        if isinstance(exc, InputValidationError):
            raise
        raise InputValidationError("CSV could not be loaded within the input limits. Check the file size and export plain UTF-8 CSV.") from exc
