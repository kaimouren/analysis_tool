"""V1 policy, input, evidence, observability and end-to-end regression contracts."""
from dataclasses import replace
import json
import logging
from pathlib import Path
from unittest.mock import patch

import httpx
import numpy as np
from openai import APITimeoutError
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from analysis import AnalysisError, analyze_csv
from config import user_endpoint_allowed
from evals.run import run
from events import emit
from ingestion import InputLimits, InputValidationError, load_csv
from llm import UNAVAILABLE, explain_profile, fallback_explanations
from policy import DEFAULT_THRESHOLDS, QualityThresholds, SeverityBands
from qa_core import profile_dataframe, severity
from report import markdown_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("payload,filename,match", [
    (b"", "x.csv", "empty"), (b"a,a\n1,2", "x.csv", "duplicate"),
    (b"a,\n1,2", "x.csv", "nonblank"), (b'a,b\n"secret', "x.csv", "parse"),
    (b"a,b\n1,2,3", "x.csv", "parse"), (b"a\n1\x00", "x.csv", "encoding"),
    (b"a\n1", "x.xlsx", "Unsupported"),
])
def test_rejected_input_has_actionable_safe_error(payload, filename, match):
    with pytest.raises(InputValidationError, match=match) as error:
        load_csv(payload, filename)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("limits,payload", [
    (InputLimits(max_rows=2), b"a\n1\n2\n3"),
    (InputLimits(max_columns=1), b"a,b\n1,2"),
    (InputLimits(max_cells=3), b"a,b\n1,2\n3,4"),
    (InputLimits(max_frame_bytes=1), b"a\n1"),
])
def test_limits_reject_instead_of_silently_sampling(limits, payload):
    with pytest.raises(InputValidationError):
        load_csv(payload, limits=limits)


def test_unicode_latin1_null_tokens_and_header_only():
    frame, encoding = load_csv("name,value\n東京,NA\ncafé,null\n🙂,3\n".encode("utf-8"))
    assert encoding == "utf-8" and frame.value.isna().sum() == 2
    assert frame.name.tolist() == ["東京", "café", "🙂"]
    frame, encoding = load_csv("name\ncafé".encode("latin-1"))
    assert encoding == "latin-1" and frame.iloc[0, 0] == "café"
    assert profile_dataframe(load_csv(b"a,b\n")[0])["quality_score"] == 0


@pytest.mark.parametrize("kind", ["missingness", "duplicates", "outliers", "mixed_type"])
def test_every_percentage_severity_boundary(kind):
    bands = DEFAULT_THRESHOLDS.bands(kind)
    ordered = [(name, value) for name, value in bands.items() if value is not None]
    previous = "low"
    for level, threshold in ordered:
        # Zero is a detection gate: no issue is emitted at zero; positive mixtures begin medium.
        if threshold:
            assert severity(threshold - .000001, **bands) == previous
        assert severity(threshold, **bands) == level
        assert severity(threshold + .000001, **bands) == level
        previous = level


def test_concentration_and_uniqueness_boundaries_and_override():
    for count, detected in [(94, False), (95, True), (96, True)]:
        profile = profile_dataframe(pd.DataFrame({"x": ["a"] * count + ["b"] * (100-count)}))
        assert profile["columns"][0]["near_constant"] is detected
        profile = profile_dataframe(pd.DataFrame({"x": [f"code_{i}" for i in range(count)] + ["code_0"] * (100-count)}))
        assert profile["columns"][0]["possible_id"] is detected
    frame = pd.DataFrame({"x": [None] * 10 + list(np.linspace(.1, 9.9, 90))})
    policy = replace(DEFAULT_THRESHOLDS, missingness=SeverityBands(15, 30, 60))
    result = profile_dataframe(frame, thresholds=policy)
    missing = next(i for i in result["issues"] if i["issue_type"] == "missingness")
    assert missing["severity"] == "low"
    assert result["thresholds"]["missingness"]["medium"] == 15
    assert "< 15%" in missing["severity_rule"]
    with pytest.raises(ValueError):
        QualityThresholds(iqr_multiplier=-1)
    with pytest.raises(ValueError):
        SeverityBands(20, 10)


def test_string_evidence_is_advisory_and_unscored():
    frame = pd.DataFrame({"x": ["North", "north", " North ", " ", "South"] * 20,
                          "signal": np.linspace(.01, 1.99, 100)})
    profile = profile_dataframe(frame)
    counts = {i["issue_type"]: i["evidence"]["count"] for i in profile["issues"]}
    assert counts == {"blank_strings": 20, "case_variants": 60, "surrounding_whitespace": 20}
    assert profile["quality_score"] == 100
    assert all(i["category"] == "heuristic_warning" and i["confidence"] and i["evidence"] for i in profile["issues"])


def test_score_cases_and_row_count_normalization():
    clean = pd.DataFrame({"x": np.linspace(.01, 1.99, 100)})
    minor = clean.copy()
    minor.loc[0, "x"] = np.nan
    severe = clean.copy()
    severe.loc[:59, "x"] = np.nan
    # A distinct continuous anchor prevents missing rows from becoming exact duplicates.
    for frame in (clean, minor, severe):
        frame["anchor"] = np.linspace(.02, 2.98, 100)
    assert profile_dataframe(clean)["quality_score"] == 100
    assert profile_dataframe(minor)["quality_score"] == 99.85
    assert profile_dataframe(severe)["quality_score"] == 91
    wide = pd.concat([minor.x.rename(f"x_{i}") for i in range(20)] + [minor.anchor], axis=1)
    assert profile_dataframe(wide)["quality_score"] == 99.71
    larger = pd.DataFrame({"x": [None]*120 + list(np.linspace(.01, 1.99, 80)), "anchor": np.linspace(.02, 2.98, 200)})
    assert profile_dataframe(larger)["quality_score"] == 91
    assert run()["passed"]  # Multiple issue classes and explicitly expected scores.


def test_analysis_metadata_and_report_cover_every_issue():
    data = (ROOT / "examples/messy_sample.csv").read_bytes()
    result = analyze_csv(data, "sample.csv")
    second = analyze_csv(data, "sample.csv")
    assert result.profile == second.profile
    assert result.metadata.started_at_utc and result.metadata.duration_seconds > 0
    report = markdown_report(result.profile, metadata=result.metadata)
    assert report.count("Suggested fix:") == len(result.profile["issues"]) > 5
    assert result.metadata.started_at_utc in report
    for heading in ("Methodology", "Issue summary", "Detailed findings", "Limitations", "Application version"):
        assert heading in report


def test_internal_failure_chains_cause_without_displaying_it():
    with patch("analysis.qa_core.profile_dataframe", side_effect=RuntimeError("PRIVATE_SENTINEL")):
        with pytest.raises(AnalysisError) as error:
            analyze_csv(b"x\n1", "x.csv")
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert str(error.value.__cause__) == "PRIVATE_SENTINEL"


def test_structured_logs_never_accept_content(caplog):
    logger = logging.getLogger("data_qa")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger="data_qa"):
            analyze_csv(b"PRIVATE_COLUMN\nPRIVATE_SENTINEL", "private_filename.csv")
            with pytest.raises(ValueError):
                emit("llm_failed", reason="PRIVATE_KEY", filename="private_filename.csv", api_key="PRIVATE_KEY")
            with pytest.raises(ValueError):
                emit("llm_failed", reason="PRIVATE_KEY")
            emit("llm_failed", reason="timeout")
        messages = [r.message for r in caplog.records if r.name == "data_qa"]
        serialized = " ".join(messages)
        assert "PRIVATE" not in serialized and "private_filename" not in serialized
        events = [json.loads(message) for message in messages]
        assert {e["event"] for e in events} >= {"file_loaded", "analysis_started", "checks_completed", "llm_failed"}
    finally:
        logger.removeHandler(caplog.handler)


def test_mocked_llm_success_numeric_rejection_and_timeout():
    profile = profile_dataframe(pd.DataFrame({"x": ["a", "a"]}))
    with patch("llm.OpenAI") as provider:
        parser = provider.return_value.__enter__.return_value.chat.completions.parse
        parser.return_value.choices[0].message.parsed = fallback_explanations(profile)
        assert explain_profile(profile, api_key="test-placeholder")[1].startswith("AI explanations available")
        parser.return_value.choices[0].message.parsed.score_explanation = "Quality is 99 percent."
        assert explain_profile(profile, api_key="test-placeholder")[1] == UNAVAILABLE
        parser.side_effect = APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))
        assert explain_profile(profile, api_key="test-placeholder")[1] == UNAVAILABLE


def test_endpoint_allowlist_blocks_browser_controlled_egress(monkeypatch):
    monkeypatch.setenv("QA_ALLOWED_LLM_BASE_URLS", "https://approved.invalid/v1")
    assert user_endpoint_allowed("https://api.openai.com/v1")
    assert user_endpoint_allowed("https://approved.invalid/v1/")
    assert not user_endpoint_allowed("http://169.254.169.254/latest/meta-data")
    assert not user_endpoint_allowed("https://approved.invalid/v1?secret=x")
    assert not user_endpoint_allowed("https://user:pass@approved.invalid/v1")


def test_malformed_input_ui_has_actionable_error_without_traceback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with patch("qa_core.load_csv", side_effect=InputValidationError("Could not parse CSV. Check commas and quotes.")):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.toggle[0].set_value(True).run()
    assert not app.exception
    assert any("Check commas" in error.value for error in app.error)
    assert not app.get("download_button")
