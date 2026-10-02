"""Streamlit investigation consent, real controller integration and stale state."""
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from evals.investigation import ScriptedPlanner, metric

ROOT = Path(__file__).resolve().parents[1]


def app(monkeypatch, key=''):
    monkeypatch.setenv('OPENAI_API_KEY', key)
    ui = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
    ui.radio[0].set_value('Investigate Dataset').run()
    next(t for t in ui.toggle if t.label == 'Explore the investigation sample').set_value(True).run()
    return ui


def run_button(ui):
    return next(b for b in ui.button if b.label == 'Run investigation')


def test_no_key_disabled_and_other_modes_remain(monkeypatch):
    ui = app(monkeypatch)
    ui.checkbox[0].check().run()
    assert run_button(ui).disabled
    assert any('requires a configured model' in x.value for x in ui.info)
    assert 'investigation_result' not in ui.session_state
    ui.radio[0].set_value('Single Dataset QA').run()
    ui.toggle[0].set_value(True).run()
    assert not ui.exception and ui.metric


def test_consent_controller_trace_export_and_input_reset(monkeypatch):
    ui = app(monkeypatch, 'test-placeholder')
    assert run_button(ui).disabled
    ui.checkbox[0].check().run()
    assert not run_button(ui).disabled
    planner = ScriptedPlanner([('compare_time_periods', metric()), ('compare_segments', metric(segment_columns=['device', 'country']))])
    with patch('agent.OpenAIPlanner', return_value=planner):
        run_button(ui).click().run()
    assert not ui.exception
    result = ui.session_state['investigation_result']
    assert result['status'] == 'completed' and '[ev_01]' in result['answer']
    assert ui.dataframe and ui.json and ui.get('download_button')
    ui.text_area[0].set_value('Another question about 2024 conversion').run()
    assert not ui.get('download_button') and 'investigation_result' not in ui.session_state


@pytest.mark.parametrize('failure', [RuntimeError('PRIVATE_FAILURE'), ValueError('PRIVATE_FAILURE')])
def test_failure_has_no_raw_exception_or_stale_download(monkeypatch, failure):
    ui = app(monkeypatch, 'test-placeholder')
    ui.checkbox[0].check().run()
    with patch('investigation_ui.investigate', side_effect=failure):
        run_button(ui).click().run()
    assert not ui.exception
    assert ui.error and 'PRIVATE_FAILURE' not in ui.error[0].value
    assert not ui.get('download_button')
