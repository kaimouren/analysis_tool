"""Release boundaries: independent severity, raw-token privacy and portable assets."""
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from analysis import analyze_csv
from ingestion import RAW_SAMPLE_CHARS, RAW_SAMPLE_ROWS, RAW_SAMPLE_VALUES, load_csv
from llm import UNAVAILABLE, explanation_payload, fallback_explanations
from qa_core import profile_dataframe
from report import markdown_report

ROOT = Path(__file__).resolve().parents[1]


def test_high_score_critical_counts_are_prominent_in_ui(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    frame = pd.DataFrame({f"x{i}": np.linspace(.01, 1.99, 100) for i in range(199)})
    frame["empty"] = None
    p = profile_dataframe(frame)
    assert p["quality_score"] == 99.85
    assert p["summary"]["severity_counts"] == {"critical": 1, "high": 0, "medium": 0, "low": 0}
    with patch("qa_core.load_csv", return_value=(frame, "utf-8")):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.toggle[0].set_value(True).run()
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Quality Score / 100"] == "100" and metrics["Critical Issues"] == "1"
    assert any("regardless of the aggregate score" in error.value for error in app.error)
    assert "Local issue counts: critical: 1" in markdown_report(p)


@pytest.mark.parametrize("tokens,risk", [
    (["00123", "123", "unknown"], "leading-zero"),
    (["9007199254740993", "9007199254740995"], "large integer"),
    (["NA", "null", "ordinary"], "NA-like"),
    (["$12.00", "12", "unknown"], "currency/percentage"),
    (["12%", "12", "unknown"], "currency/percentage"),
    (["01/02/2024", "02/03/2024", "unknown"], "date-like"),
])
def test_pre_inference_samples_explain_ambiguity_without_changing_facts(tokens, risk):
    result = analyze_csv(("value\n"+"\n".join(tokens)).encode(), "x.csv")
    p = result.profile
    raw = p["columns"][0]["raw_representation"]
    assert tokens[0] in raw["examples"]
    assert any(risk in label for label in raw["risks"])
    before = result.frame.copy()
    before.attrs.clear()
    clean_profile = profile_dataframe(before)
    assert p["quality_score"] == clean_profile["quality_score"]
    assert p["issues"] == clean_profile["issues"]
    serialized = json.dumps(explanation_payload(p))
    assert tokens[0] not in serialized


def test_numeric_leading_zeros_survive_only_in_bounded_source_examples():
    frame, _ = load_csv(b"identifier\n00123\n00456\n")
    p = profile_dataframe(frame)
    assert frame.iloc[0, 0] == 123
    assert p["columns"][0]["raw_representation"]["examples"] == ["00123", "00456"]
    assert "00123" not in markdown_report(p)


def test_raw_samples_are_bounded_and_excluded_from_provider_and_export():
    tokens = [f"PRIVATE-{i}-" + "x"*150 for i in range(RAW_SAMPLE_ROWS)] + ["00123456789"]
    result = analyze_csv(("value\n"+"\n".join(tokens)).encode(), "x.csv")
    sample = result.frame.attrs["qa_raw_samples"]["value"]
    assert len(sample["examples"]) <= RAW_SAMPLE_VALUES
    assert all(len(token) <= RAW_SAMPLE_CHARS for token in sample["examples"])
    assert "00123456789" not in sample["examples"]  # Sampling is explicitly early-record bounded.
    assert "PRIVATE" not in json.dumps(explanation_payload(result.profile))
    assert "PRIVATE" not in markdown_report(result.profile)


def test_generated_label_and_failure_fallback_preserve_fact_cards(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.toggle[0].set_value(True).run()
    with patch("llm.OpenAI") as provider:
        parser = provider.return_value.__enter__.return_value.chat.completions.parse
        parser.side_effect = ValueError("PRIVATE_PROVIDER_ERROR")
        app.button[0].click().run()
    assert not app.exception
    assert any(UNAVAILABLE == c.value for c in app.caption)
    assert any("Observed fact:" in t.value for t in app.text)
    assert not any("PRIVATE_PROVIDER_ERROR" in t.value for t in app.text)
    assert app.get("download_button")
    p = app.session_state["profile"]
    with patch("llm.OpenAI") as provider:
        provider.return_value.__enter__.return_value.chat.completions.parse.return_value.choices[0].message.parsed = fallback_explanations(p)
        app.button[0].click().run()
    assert not app.exception
    assert any("Generated interpretation. Verify before acting." == c.value for c in app.caption)


def test_sample_resolves_when_launched_outside_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == "Rows") == "500"
