"""One question, one bounded investigation; observable trace and evidence only."""
import hashlib
import json

import pandas as pd
import streamlit as st

from agent import investigate
from agent_models import DEFAULT_AGENT_LIMITS
from config import validate_upload_size
from ingestion import InputValidationError, load_csv


def investigation_sample():
    rows = []
    for month in (2, 3):
        for device in ('mobile', 'desktop'):
            for country in ('US', 'CA'):
                positives = 10 if month == 3 and device == 'mobile' and country == 'US' else 30
                rows.extend({'date': f'2024-{month:02d}-15', 'device': device, 'country': country,
                             'conversion': int(n < positives), 'revenue': float(10 if n < positives else 0)} for n in range(40))
    return pd.DataFrame(rows)


def render_investigation(api_key, model, base_url):
    st.title('Investigate a question about this dataset')
    st.caption('One question → bounded tool investigation → cited observations. The model chooses analyses; deterministic code computes and renders factual claims.')
    upload = st.file_uploader('Investigation dataset', type=['csv'], key='investigation_upload')
    sample = st.toggle('Explore the investigation sample', key='investigation_sample')
    question = st.text_area('Question', value='Why did conversion drop in March 2024 compared with February 2024?', max_chars=2000, key='investigation_question')
    st.caption('Use explicit years, metric names and intended aggregation where possible. Rates require binary zero/one or boolean data. UTC periods include the start and exclude the end.')
    consent = st.checkbox('Allow sending this question, column names/types and bounded aggregate evidence (including group labels) to the configured model.', key='investigation_consent')
    st.caption('No raw-row tool, code execution, filesystem access or persistent investigation history. Aggregates and labels can still be sensitive. Only observable actions are shown, never hidden reasoning.')
    if not api_key:
        st.info('Investigation requires a configured model/API key. Single Dataset QA and Compare Against Baseline still work without one.')
    blob, name = None, None
    if upload is not None:
        try:
            validate_upload_size(upload.size)
            blob, name = upload.getvalue(), upload.name
        except ValueError as exc:
            st.error(str(exc))
    elif sample:
        blob, name = investigation_sample().to_csv(index=False).encode(), 'investigation_sample.csv'
    identity = (hashlib.sha256(blob).hexdigest() if blob else None, name, question)
    if st.session_state.get('investigation_input') != identity:
        st.session_state.pop('investigation_result', None)
        st.session_state['investigation_input'] = identity
    limits = DEFAULT_AGENT_LIMITS
    st.caption(f'Limits: {limits.max_steps} planning steps, {limits.max_tool_calls} tool calls, {limits.max_tool_errors} errors. Up to 80 columns; existing upload limits apply.')
    if st.button('Run investigation', disabled=not (api_key and consent and blob and question.strip()), key='run_investigation'):
        st.session_state.pop('investigation_result', None)
        try:
            frame, _ = load_csv(blob, name)
            with st.spinner('Investigating with bounded deterministic tools…'):
                result = investigate(frame, question, api_key=api_key, model=model, base_url=base_url)
            st.session_state['investigation_result'] = result
        except InputValidationError as exc:
            st.error(str(exc))
        except Exception:
            st.error('Investigation could not complete safely. QA and comparison remain available.')
    result = st.session_state.get('investigation_result')
    if result:
        st.subheader('Investigation ' + result['status'])
        st.caption('Completion refers to the supported descriptive checks, not proof of cause or guaranteed interpretation of the question.')
        st.text(result['answer'])
        with st.expander('Observable investigation trace', expanded=True):
            st.dataframe(pd.DataFrame(result['steps']).astype(str), hide_index=True, width='stretch')
        with st.expander('Cited evidence and exact interpreted arguments'):
            for item in result['evidence']:
                st.text(item['evidence_id'] + ' · ' + item['tool'])
                st.json(item)
        with st.expander('Limits and execution metrics'):
            st.json({'metrics': result['metrics'], 'stop_reason': result['stop_reason'], 'limitations': result['limitations']})
        st.download_button('Download investigation evidence', json.dumps(result, indent=2, allow_nan=False), 'investigation.json', 'application/json')
        st.caption('The export contains the question, column/group names and aggregate evidence. Review before sharing; nothing is saved to local history automatically.')
