"""Deployment boundaries without network calls or real credentials."""
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from config import MAX_UPLOAD_BYTES, resolve_setting, validate_upload_size
from llm import UNAVAILABLE, explain_profile, fallback_explanations
from qa_core import load_csv, profile_dataframe

ROOT = Path(__file__).resolve().parents[1]


def test_configuration_precedence_and_absent_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "environment-model")
    assert resolve_setting("OPENAI_MODEL", "sidebar-model", secrets={"OPENAI_MODEL": "secret-model"}) == "sidebar-model"
    assert resolve_setting("OPENAI_MODEL", secrets={"OPENAI_MODEL": "secret-model"}) == "environment-model"
    monkeypatch.delenv("OPENAI_MODEL")
    assert resolve_setting("OPENAI_MODEL", secrets={"OPENAI_MODEL": "secret-model"}) == "secret-model"
    missing = MagicMock()
    missing.get.side_effect = FileNotFoundError()
    assert resolve_setting("OPENAI_MODEL", secrets=missing, default="default") == "default"


def test_upload_limit_rejects_before_csv_parsing():
    validate_upload_size(MAX_UPLOAD_BYTES)
    with pytest.raises(ValueError, match="10 MiB"):
        validate_upload_size(MAX_UPLOAD_BYTES + 1)
    with patch("qa_core.pd.read_csv") as reader:
        with pytest.raises(ValueError, match="10 MiB"):
            load_csv(b"x" * (MAX_UPLOAD_BYTES + 1))
        reader.assert_not_called()


def test_one_column_categorical_and_all_null_data():
    profile = profile_dataframe(pd.DataFrame({"category": ["a", "b", "a", None]}))
    assert profile["columns"][0]["numeric_stats"] == {}
    assert profile["summary"]["columns"] == 1
    assert profile["summary"]["duplicate_rows"] == 1
    empty = profile_dataframe(pd.DataFrame({"empty": [None, None]}))
    assert any(i["severity"] == "critical" and i["issue_type"] == "missingness" for i in empty["issues"])


def test_invalid_provider_output_preserves_profile():
    profile = profile_dataframe(pd.DataFrame({"constant": ["a", "a"]}))
    before = copy.deepcopy(profile)
    with patch("llm.OpenAI") as provider:
        response = provider.return_value.__enter__.return_value.chat.completions.parse.return_value
        response.choices[0].message.parsed = fallback_explanations(profile)
        response.choices[0].message.parsed.issues[0].issue_id = "unknown"
        _, status = explain_profile(profile, api_key="test-placeholder")
    assert status == UNAVAILABLE
    assert profile == before


def test_server_credentials_stay_out_of_widgets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert app.text_input[0].value == ""
    app.toggle[0].set_value(True).run()
    app.text_input[2].set_value("https://example.invalid/v1").run()
    assert not app.exception
    assert app.button[0].disabled
    assert any("own API key" in warning.value for warning in app.warning)


def test_streamlit_secrets_fallback(monkeypatch):
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
        monkeypatch.delenv(name, raising=False)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    app.secrets["OPENAI_API_KEY"] = "test-placeholder"
    app.secrets["OPENAI_MODEL"] = "configured-model"
    app.run()
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert not app.button[0].disabled
    assert app.text_input[0].value == ""
