"""Presentation and explicit local persistence for deterministic comparisons."""
import hashlib
import json
import os
import uuid

import pandas as pd
import streamlit as st

from comparison import compare_datasets
from comparison_llm import explain_comparison, fallback_comparison
from config import validate_upload_size
from history import HistoryError, recent_runs, save_run
from ingestion import InputValidationError, load_csv
from report import escape


STATUS_LABELS = {'low': 'Low observed drift', 'moderate': 'Moderate observed drift',
                 'high': 'High observed drift', 'not_comparable': 'Insufficient comparable data'}


def _display(value, signed=False):
    if value is None:
        return 'N/A'
    if isinstance(value, (float, int)):
        return format(value, '+.4g' if signed else '.4g')
    return str(value)


def comparison_report(result):
    lines = ['# Baseline comparison', '', 'Overall drift: ' + STATUS_LABELS[result['summary']['status']],
             '', 'Heuristic summary, not statistical significance, business impact or causality. Direction: current minus baseline.',
             '', '## Dataset metrics', '', '| Metric | Baseline | Current | Absolute change | Relative change % |',
             '|---|---:|---:|---:|---:|']
    for name, values in result['dataset_metrics'].items():
        lines.append('| ' + ' | '.join([name] + [str(values[k]) if values[k] is not None else 'N/A' for k in ('baseline', 'current', 'absolute_change', 'relative_change_pct')]) + ' |')
    lines += ['', 'Rate differences above are percentage points. A zero baseline has no relative percent change.', '', '## Findings', '']
    for f in result['findings']:
        lines += [f"- {f['severity']}: {escape(f['kind'])} — {escape(f['column'] or 'Dataset')}",
                  '  Evidence: ' + escape(json.dumps(f['evidence'], allow_nan=False))]
    lines += ['', '## Method', '', 'KS is the maximum empirical CDF gap; categorical TVD is half the sum of absolute probability differences. All rows are used. No p-values. Tiny non-null samples are not assigned distribution severity. High-cardinality category composition is suppressed. Datetime coverage uses conservative year-first parsing, not a business calendar.',
              '', 'Thresholds: ' + escape(json.dumps(result['policy'], sort_keys=True)),
              '', 'Reports contain column names but omit category labels and generated prose. Review before sharing.']
    return '\n'.join(lines)


def _sample():
    baseline = pd.DataFrame({'revenue': [float(n) for n in range(100)], 'device': ['desktop'] * 60 + ['mobile'] * 40,
                             'email_present': ['yes'] * 100, 'date': pd.date_range('2024-01-01', periods=100).astype(str)})
    current = baseline.copy()
    current['revenue'] += 50
    current['device'] = ['desktop'] * 20 + ['mobile'] * 80
    current.loc[:29, 'email_present'] = None
    return baseline, current


def render_comparison(api_key, model, base_url):
    st.title('What changed against the baseline?')
    st.caption('Compare dataset versions. Distribution change does not establish business impact, statistical significance or a cause.')
    left, right = st.columns(2)
    baseline = left.file_uploader('Baseline dataset', type=['csv'], key='baseline_upload')
    current = right.file_uploader('Current dataset', type=['csv'], key='current_upload')
    sample = st.toggle('Explore a comparison example', key='comparison_sample')
    st.caption('Each CSV: up to 10 MiB, 200,000 rows, 200 columns and 2 million cells. Both datasets are held in server memory. No row matching or automatic cleaning.')
    if sample and baseline is None and current is None:
        a, b = _sample()
        blobs = (a.to_csv(index=False).encode(), b.to_csv(index=False).encode())
        names = ('baseline_example.csv', 'current_example.csv')
    elif baseline is not None and current is not None:
        try:
            validate_upload_size(baseline.size)
            validate_upload_size(current.size)
        except ValueError as exc:
            st.error(str(exc))
            return
        blobs = (baseline.getvalue(), current.getvalue())
        names = (baseline.name, current.name)
    else:
        blobs = None
        names = None
    digest = tuple(hashlib.sha256(data).hexdigest() for data in blobs) + names if blobs else None
    if st.session_state.get('comparison_input') != digest:
        for key in ('comparison_result', 'comparison_guidance', 'comparison_saved', 'comparison_run_id'):
            st.session_state.pop(key, None)
        st.session_state['comparison_input'] = digest
    if st.button('Compare', disabled=blobs is None, key='compare_button'):
        # A failed recomputation must never leave a previous result downloadable.
        st.session_state.pop('comparison_result', None)
        st.session_state.pop('comparison_guidance', None)
        try:
            with st.spinner('Comparing baseline and current…'):
                a, _ = load_csv(blobs[0], names[0])
                b, _ = load_csv(blobs[1], names[1])
                result = compare_datasets(a, b)
            st.session_state.update(comparison_result=result, comparison_run_id=uuid.uuid4().hex)
            st.session_state.pop('comparison_guidance', None)
            st.session_state.pop('comparison_saved', None)
        except InputValidationError as exc:
            st.error(str(exc))
        except Exception:
            st.error('Comparison could not complete. Try smaller CSVs with scalar values; deterministic results were not replaced.')
    result = st.session_state.get('comparison_result')
    if result:
        st.subheader(STATUS_LABELS[result['summary']['status']])
        st.caption('Heuristic summary: any high finding or at least three moderate findings gives High; any remaining moderate gives Moderate. Informational changes alone give Low. Empty/no-overlap inputs are not comparable.')
        st.caption('Low observed drift does not mean healthy data. Small samples, all-null values and high cardinality can leave distributions unassessed; missingness decreases also count as change.')
        with st.expander('Distribution assessment coverage'):
            st.json(result['summary']['assessment_counts'])
        st.text(f'Baseline: {names[0]} → Current: {names[1]}')
        labels = {'rows': 'Rows', 'columns': 'Columns', 'duplicate_pct': 'Duplicate rate (%)', 'missing_pct': 'Missing cells (%)'}
        st.dataframe(pd.DataFrame([{'Metric': labels[k], 'Baseline': _display(v['baseline']), 'Current': _display(v['current']),
                                   'Change': _display(v['absolute_change'], signed=True), 'Relative change (%)': _display(v['relative_change_pct'], signed=True),
                                   'Change unit': v['unit'].replace('_', ' ')} for k, v in result['dataset_metrics'].items()]), hide_index=True, width='stretch')
        st.caption('Absolute differences for rates are percentage points; relative differences are percentages. N/A means a zero baseline or no denominator.')
        schema_tab, column_tab, findings_tab = st.tabs(['Schema changes', 'Column drift', 'Detailed findings'])
        with schema_tab:
            st.json(result['schema'])
        with column_tab:
            if result['columns']:
                selected = st.selectbox('Shared column', list(result['columns']), key='comparison_column')
                detail = result['columns'][selected]
                st.text(f"Parsed type: {detail['baseline']['family']} → {detail['current']['family']}")
                missing = detail['missingness']
                st.text(f"Missing: {_display(missing['baseline'])}% → {_display(missing['current'])}% · {_display(missing['absolute_change'], signed=True)} percentage points")
                unique = detail['cardinality']['unique_count']
                st.text(f"Distinct non-null values: {_display(unique['baseline'])} → {_display(unique['current'])}")
                with st.expander('Parsed column statistics'):
                    st.dataframe(pd.DataFrame({'Baseline': detail['baseline'], 'Current': detail['current']}).astype(str), width='stretch')
                if detail['numeric']:
                    numeric = detail['numeric']
                    st.text(f"KS distance: {_display(numeric['ks'])} · {numeric['assessment'].replace('_', ' ')}")
                    st.dataframe(pd.DataFrame({'Baseline': numeric['baseline'], 'Current': numeric['current']}), width='stretch')
                    st.caption(numeric['precision'])
                if detail['categorical']:
                    cat = detail['categorical']
                    st.text(f"Categorical TVD: {_display(cat['tvd'])} · {cat['status'].replace('_', ' ')}")
                    st.caption('Category frequencies exclude nulls. Labels may be truncated. High-cardinality detail is suppressed; category changes do not establish errors.')
                    st.dataframe(pd.DataFrame(cat['top_changes']), hide_index=True, width='stretch')
                    with st.expander('New and disappeared categories (bounded examples)'):
                        st.json({k: cat[k] for k in ('new_count', 'disappeared_count', 'new_examples', 'disappeared_examples')})
                if detail['datetime']:
                    st.json(detail['datetime'])
                    st.caption('Coverage uses parseable year-first timestamps in UTC. Gaps are assessed only against an exactly regular baseline cadence; no expected business schedule is known.')
        with findings_tab:
            st.dataframe(pd.DataFrame(result['findings']), hide_index=True, width='stretch')
        st.subheader('Comparison interpretation')
        if st.button('Explain comparison with AI', disabled=not api_key or not result['findings']):
            st.session_state['comparison_guidance'] = explain_comparison(result, api_key, model, base_url)
        bundle, status = st.session_state.get('comparison_guidance', (fallback_comparison(result), 'Authored guidance; no generated explanation.'))
        st.caption(status)
        st.caption('Generated interpretation. Verify before acting.' if status.startswith('AI explanations available') else 'Authored rule interpretation')
        st.text(bundle.score_explanation)
        for finding, item in zip(result['findings'][:5], bundle.issues):
            with st.expander(f"{finding['rank']}. {finding['kind']} · {finding['column'] or 'Dataset'}"):
                st.caption('Deterministic evidence')
                st.json(finding)
                st.caption('Generated interpretation. Verify before acting.' if status.startswith('AI explanations available') else 'Authored guidance')
                st.text(item.explanation)
                st.text(item.modeling_impact)
                st.text(item.suggested_fix)
        st.download_button('Download comparison report', comparison_report(result), 'comparison_report.md', 'text/markdown')
    history_path = os.getenv('QA_HISTORY_PATH', '').strip()
    with st.expander('Recent local comparison runs'):
        if not history_path:
            st.info('Persistent history is disabled. On a trusted single-user installation, set QA_HISTORY_PATH to a local SQLite file. Do not enable shared history on a public demo.')
        else:
            st.caption('Opt-in local storage: filenames, timestamp, row counts, heuristic status and finding-type counts only. No uploaded datasets, category values, column names or AI text. Most recent 50 runs; shared by users of this installation.')
            try:
                if result and st.button('Save run to local history', disabled=bool(st.session_state.get('comparison_saved'))):
                    saved = save_run(history_path, result, *names, run_id=st.session_state['comparison_run_id'])
                    st.session_state['comparison_saved'] = True
                    st.success('Comparison metadata saved.')
                    if saved['recovered_corruption']:
                        st.warning('Damaged history was preserved in a .corrupt file; a new history was created.')
                history = recent_runs(history_path)
                if history['recovered_corruption'] or history['skipped_records']:
                    st.warning('Some damaged history could not be read; valid records remain available.')
                st.dataframe(pd.DataFrame(history['runs']), hide_index=True, width='stretch')
            except HistoryError as exc:
                st.warning(str(exc))
