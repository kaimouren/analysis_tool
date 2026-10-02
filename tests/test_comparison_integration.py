"""Privacy, persistence, optional generation and the V2 Streamlit workflow."""
import copy
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from comparison import compare_datasets
from comparison_llm import comparison_payload, explain_comparison, fallback_comparison, validate_comparison_explanations
from comparison_ui import comparison_report
from history import recent_runs, save_run, HistoryError
from llm import UNAVAILABLE

ROOT = Path(__file__).resolve().parents[1]


def result():
    return compare_datasets(pd.DataFrame({'PRIVATE_COLUMN': ['PRIVATE_A'] * 30}),
                            pd.DataFrame({'PRIVATE_COLUMN': ['PRIVATE_B'] * 30}))


def test_history_roundtrip_is_bounded_metadata_and_idempotent(tmp_path):
    path = tmp_path / 'history.sqlite3'
    r = result()
    save_run(path, r, '/secret/baseline.csv', r'C:\secret\current.csv', run_id='same')
    save_run(path, r, 'other.csv', 'other.csv', run_id='same')
    records = recent_runs(path)['runs']
    assert len(records) == 1
    assert records[0]['baseline_filename'] == 'baseline.csv'
    assert records[0]['current_filename'] == 'current.csv'
    assert 'PRIVATE' not in json.dumps(records)
    for n in range(55):
        save_run(path, r, 'b.csv', 'c.csv', run_id=str(n))
    assert len(recent_runs(path)['runs']) == 50


def test_corrupted_history_is_preserved_and_recovers(tmp_path):
    path = tmp_path / 'history.sqlite3'
    path.write_bytes(b'not sqlite')
    loaded = recent_runs(path)
    assert loaded['recovered_corruption'] and loaded['runs'] == []
    assert next(tmp_path.glob('*.corrupt-*')).read_bytes() == b'not sqlite'
    save_run(path, result(), 'a', 'b')
    assert len(recent_runs(path)['runs']) == 1


def test_bad_json_history_record_is_skipped(tmp_path):
    path = tmp_path / 'history.sqlite3'
    save_run(path, result(), 'a', 'b')
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO runs VALUES ('bad', '9999', 'not JSON')")
    loaded = recent_runs(path)
    assert len(loaded['runs']) == 1 and loaded['skipped_records'] == 1


def test_history_storage_errors_are_safe(tmp_path):
    with pytest.raises(HistoryError):
        save_run(tmp_path, result(), 'a', 'b')


def test_payload_and_export_exclude_category_values():
    r = result()
    assert 'PRIVATE' not in json.dumps(comparison_payload(r))
    assert 'PRIVATE_A' not in comparison_report(r)
    assert 'PRIVATE_B' not in comparison_report(r)
    assert 'PRIVATE' in comparison_report(r)  # Column names are intentionally local/report-visible.


@pytest.mark.parametrize('prose', ['This is statistically significant.', 'This was caused by upstream errors.',
                                 'The missing rate is 99.', 'Delete all affected rows.', 'This is high drift.'])
def test_explanation_rejects_exaggeration_and_fabrication(prose):
    r = result()
    bundle = fallback_comparison(r)
    bundle.issues[0].explanation = prose
    with pytest.raises(ValueError):
        validate_comparison_explanations(bundle, r)


def test_llm_fallback_and_valid_output_cannot_mutate_results():
    r = result()
    before = copy.deepcopy(r)
    with patch('comparison_llm.OpenAI') as provider:
        parser = provider.return_value.__enter__.return_value.chat.completions.parse
        parser.side_effect = RuntimeError('PRIVATE_PROVIDER_FAILURE')
        fallback, status = explain_comparison(r, 'test-placeholder')
        assert status == UNAVAILABLE
        parser.side_effect = None
        parser.return_value.choices[0].message.parsed = fallback_comparison(r)
        generated, status = explain_comparison(r, 'test-placeholder')
        assert status.startswith('AI explanations available')
        assert generated == fallback
    assert r == before


def test_comparison_ui_and_local_history(monkeypatch, tmp_path):
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('QA_HISTORY_PATH', str(tmp_path / 'history.sqlite3'))
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    app.radio[0].set_value('Compare Against Baseline').run()
    app.toggle[0].set_value(True).run()
    next(b for b in app.button if b.label == 'Compare').click().run()
    assert not app.exception
    assert app.session_state['comparison_result']['summary']['status'] == 'high'
    assert app.get('download_button')
    assert next(b for b in app.button if b.label == 'Explain comparison with AI').disabled
    next(b for b in app.button if b.label == 'Save run to local history').click().run()
    assert not app.exception
    assert len(recent_runs(tmp_path / 'history.sqlite3')['runs']) == 1
    app.toggle[0].set_value(False).run()
    assert not app.get('download_button')
    assert 'comparison_result' not in app.session_state
    app.radio[0].set_value('Single Dataset QA').run()
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == 'Rows') == '500'


def test_comparison_ui_failure_no_stacktrace_or_stale_download(monkeypatch):
    monkeypatch.delenv('QA_HISTORY_PATH', raising=False)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    app.radio[0].set_value('Compare Against Baseline').run()
    app.toggle[0].set_value(True).run()
    next(b for b in app.button if b.label == 'Compare').click().run()
    assert app.get('download_button')
    with patch('comparison_ui.compare_datasets', side_effect=RuntimeError('PRIVATE_FAILURE')):
        next(b for b in app.button if b.label == 'Compare').click().run()
    assert not app.exception
    assert app.error and 'PRIVATE_FAILURE' not in app.error[0].value
    assert not app.get('download_button')


def test_locked_history_is_not_renamed_or_reset(tmp_path):
    path = tmp_path / 'history.sqlite3'
    save_run(path, result(), 'a', 'b')
    original_connect = sqlite3.connect
    connection = original_connect(path)
    connection.execute('BEGIN EXCLUSIVE')
    try:
        with patch('history.sqlite3.connect', side_effect=lambda path, timeout: original_connect(path, timeout=.01)):
            with pytest.raises(HistoryError):
                recent_runs(path)
        assert not list(tmp_path.glob('*.corrupt-*'))
    finally:
        connection.rollback()
        connection.close()
    assert len(recent_runs(path)['runs']) == 1


def test_wrongly_typed_history_json_is_skipped(tmp_path):
    path = tmp_path / 'history.sqlite3'
    save_run(path, result(), 'a', 'b')
    with sqlite3.connect(path) as conn:
        conn.execute('UPDATE runs SET body=?', (json.dumps({'run_id': [], 'created_at': 1, 'status': 'high', 'baseline_filename': {}, 'current_filename': []}),))
    loaded = recent_runs(path)
    assert loaded['runs'] == [] and loaded['skipped_records'] == 1


def test_comparison_ui_generated_label_and_rejected_output(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    monkeypatch.delenv('QA_HISTORY_PATH', raising=False)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    app.radio[0].set_value('Compare Against Baseline').run()
    app.toggle[0].set_value(True).run()
    next(b for b in app.button if b.label == 'Compare').click().run()
    original = copy.deepcopy(app.session_state['comparison_result'])
    with patch('comparison_llm.OpenAI') as provider:
        parsed = provider.return_value.__enter__.return_value.chat.completions.parse.return_value.choices[0].message
        parsed.parsed = fallback_comparison(original)
        next(b for b in app.button if b.label == 'Explain comparison with AI').click().run()
        assert any(c.value == 'Generated interpretation. Verify before acting.' for c in app.caption)
        parsed.parsed.issues[0].explanation = 'This is caused by deployment errors.'
        next(b for b in app.button if b.label == 'Explain comparison with AI').click().run()
        assert any(c.value == UNAVAILABLE for c in app.caption)
    assert not app.exception
    assert app.get('download_button')
    assert app.session_state['comparison_result'] == original
