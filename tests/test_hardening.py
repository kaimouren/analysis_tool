"""Adversarial examples for the first-pass screening contract."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from llm import explanation_payload
from presentation import SCOPE_NOTE
from qa_core import load_csv, profile_dataframe
from report import markdown_report

ROOT = Path(__file__).resolve().parents[1]


def test_high_score_does_not_mask_critical_local_finding():
    frame = pd.DataFrame({f"feature_{i}": np.linspace(.1, 9.9, 100) + i/1000 for i in range(99)})
    frame["unused"] = None
    profile = profile_dataframe(frame)
    assert profile["quality_score"] == 99.7
    assert profile["score_breakdown"]["missingness"] == .3
    assert profile["review_status"].startswith("Critical")
    assert profile["summary"]["max_column_missing_pct"] == 100
    assert profile["summary"]["max_missing_column"] == "unused"


def test_clean_dataset_means_no_rule_findings_not_validation():
    profile = profile_dataframe(pd.DataFrame({"signal": np.linspace(.01, 1.99, 100)}))
    assert profile["issues"] == []
    assert profile["quality_score"] == 100
    assert profile["review_status"] == "No findings under the implemented rules"
    report = markdown_report(profile)
    assert SCOPE_NOTE in report
    assert "not a percentage of valid data" in report


def test_mixed_parser_evidence_and_csv_inference_are_distinct():
    frame = pd.DataFrame({"codes": ["00123", "1", "1.5", "N/A", "unknown", "$12", "15%"]})
    profile = profile_dataframe(frame)
    evidence = profile["columns"][0]["semantic_evidence"]
    assert evidence["counts"] == {"numeric_parseable": 3, "date_parseable": 0, "neither_parseable": 4}
    assert evidence["leading_zero_integer_count"] == 1
    assert evidence["currency_like_count"] == 1
    assert evidence["percentage_like_count"] == 1
    loaded, _ = load_csv(b"code\n00123\nN/A\n")
    assert loaded["code"].isna().sum() == 1
    assert loaded["code"].iloc[0] == 123  # Loader inference is explicitly documented.
    for values, semantic in [(["00123", "00456"], "identifier-like text"), (["1", "1.5"], "numeric-like text")]:
        assert profile_dataframe(pd.DataFrame({"x": values}))["columns"][0]["semantic_type"] == semantic


def test_dates_measure_parser_success_not_semantic_correctness():
    profile = profile_dataframe(pd.DataFrame({"dates": ["01/02/2024", "03/04/05", "2024-03-01", "unknown"]}))
    assert profile["columns"][0]["datetime_parseability_pct"] == 50
    assert profile["columns"][0]["semantic_type"] == "mixed"
    for n, semantic in [(16, "mixed"), (19, "datetime-like")]:
        profile = profile_dataframe(pd.DataFrame({"d": ["01/02/2024"]*n + ["unknown"]*(20-n)}))
        assert profile["columns"][0]["semantic_type"] == semantic
    native = profile_dataframe(pd.DataFrame({"d": pd.date_range("2024-01-01", periods=2)}))
    assert native["columns"][0]["semantic_type"] == "datetime-like"


def test_id_evidence_does_not_establish_an_identifier():
    profile = profile_dataframe(pd.DataFrame({"customer_id": range(20), "product_name": [f"product_{i}" for i in range(20)]}))
    customer, product = profile["columns"]
    assert customer["id_evidence"]["name_hint"]
    assert customer["id_evidence"]["unit_step_integer_sequence"]
    assert product["possible_id"] and not product["id_evidence"]["name_hint"]
    assert not product["id_evidence"]["role_established"]


def test_added_local_evidence_never_reaches_the_model():
    profile = profile_dataframe(pd.DataFrame({"private_column": ["123", "PRIVATE_SENTINEL", "456"]}))
    assert "PRIVATE_SENTINEL" in json.dumps(profile)
    # Defend against future evidence added directly to issue records too.
    profile["issues"][0]["examples"] = ["PRIVATE_SENTINEL"]
    serialized = json.dumps(explanation_payload(profile))
    assert "PRIVATE_SENTINEL" not in serialized and "private_column" not in serialized


def test_severity_rule_and_report_preserve_facts():
    profile = profile_dataframe(pd.DataFrame({"value": [None]*5 + list(range(5))}))
    issue = next(i for i in profile["issues"] if i["issue_type"] == "missingness")
    assert issue["severity"] == "critical"
    assert ">= 50%" in issue["severity_rule"]
    assert issue["evidence"]["count"] == 5 and issue["evidence"]["denominator"] == 10
    report = markdown_report(profile)
    for text in ("Observed fact:", "Severity rule:", "Interpretation (authored rule guidance)", "Suggested fix:", "Column missingness", "cap 30", "score policy: 1.0"):
        assert text in report


def test_skewed_tiny_and_messy_scores_remain_reproducible():
    cases = [(pd.DataFrame({"x": np.exp(np.linspace(0, 8, 100))}), 89.5),
             (pd.DataFrame({"x": [1]}), 82.0),
             (load_csv((ROOT / "examples/messy_sample.csv").read_bytes())[0], 92.36)]
    for frame, expected in cases:
        before = copy.deepcopy(frame)
        profile = profile_dataframe(frame)
        assert profile["quality_score"] == expected
        assert json.dumps(profile, allow_nan=False) == json.dumps(profile_dataframe(frame), allow_nan=False)
        pd.testing.assert_frame_equal(frame, before)
    assert profile_dataframe(cases[1][0])["context_notes"]


@pytest.mark.parametrize("frame, chart_count", [
    (pd.DataFrame({"x": [None, None]}), 0),
    (pd.DataFrame(columns=["x"]), 0),
    (pd.DataFrame({"x": [np.inf, -np.inf]}), 0),
    (pd.DataFrame({"x": [1]}), 1),
    (pd.DataFrame({"x": ["a", "b", "c"]}), 1),
    (pd.DataFrame({"x": np.linspace(.01, 1.99, 100)}), 1),
])
def test_edge_case_ui_keeps_report_available(monkeypatch, frame, chart_count):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    with patch("qa_core.load_csv", return_value=(frame, "utf-8")):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.toggle[0].set_value(True).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == chart_count
    assert len(app.get("download_button")) == 1
    if not chart_count:
        assert any("to plot" in message.value for message in app.info)
