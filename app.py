"""Streamlit presentation only; calculations live in qa_core."""
import hashlib
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from llm import UNAVAILABLE, explain_profile, fallback_explanations
from analysis import analyze_csv, AnalysisError
from ingestion import InputValidationError
from events import configure_logging
from policy import PROFILE_VERSION
from report import markdown_report, trigger
from config import DEFAULT_MODEL, MAX_UPLOAD_MB, resolve_setting, validate_upload_size, user_endpoint_allowed
from presentation import SCOPE_NOTE, ISSUE_CAVEATS, issue_title, observation, penalty_rows

st.set_page_config(page_title="Data QA Agent", page_icon="🔎", layout="wide")
configure_logging()
st.markdown("""<style>
    .stApp {background: #f6f8fc;}
    h1, h2, h3 {color: #152b45;}
    [data-testid="stMetric"] {background: white; border: 1px solid #dce3ee;
      border-radius: 12px; padding: 16px;}
    [data-testid="stSidebar"] {background: #eaf0f8;}
    .block-container {padding-top: 4rem;}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Data QA Agent")
    st.caption("Evidence for a first review")
    # Server credentials must never be copied into a browser-visible widget.
    server_key = resolve_setting("OPENAI_API_KEY", secrets=st.secrets)
    server_url = resolve_setting("OPENAI_BASE_URL", secrets=st.secrets)
    user_key = st.text_input("API key (optional)", type="password",
                             help="Leave blank to use server configuration, if available.")
    model_input = st.text_input("Model", placeholder=resolve_setting("OPENAI_MODEL", secrets=st.secrets, default=DEFAULT_MODEL))
    url_input = st.text_input("Base URL (optional)", help="A different provider endpoint requires your own API key.")
    api_key = resolve_setting("OPENAI_API_KEY", user_key, secrets=st.secrets)
    model = resolve_setting("OPENAI_MODEL", model_input, secrets=st.secrets, default=DEFAULT_MODEL)
    base_url = resolve_setting("OPENAI_BASE_URL", url_input, secrets=st.secrets)
    # A visitor-controlled URL must not receive the deployment's private key.
    endpoint_changed = bool(url_input.strip() and base_url.rstrip("/") != (server_url or "https://api.openai.com/v1").rstrip("/"))
    if endpoint_changed and not user_key.strip() and server_key:
        api_key = ""
        st.warning("Enter your own API key to use a different provider endpoint.")
    if url_input.strip() and not user_endpoint_allowed(base_url, server_url):
        api_key = ""
        st.warning("This endpoint is not enabled by the deployment administrator. Use the configured provider or an approved endpoint.")
    st.divider()
    st.info("Statistics and score are deterministic; the LLM only explains results.")
    st.caption("AI explanations send aggregate statistics and anonymous column aliases to the configured provider. No raw rows or column names are sent.")
    st.caption("Suggestions only. No cleaning is applied; CSV parsing can normalize types and missing tokens.")

st.caption("EXPLORATORY DATA QA / BEFORE YOU MODEL")
st.title("What deserves a closer look?")
st.write("A first-pass health check for common structural and statistical dataset risks.")
st.caption("Upload one CSV with a header. These checks do not establish domain correctness, leakage, fairness, or modeling readiness.")
upload = st.file_uploader("Upload a CSV", type=["csv"])
st.caption(f"Up to {MAX_UPLOAD_MB} MiB, 200,000 rows, 200 columns and 2 million cells. Uploads stay in server memory; they are not saved to disk.")
use_sample = st.toggle("Explore the messy sample", value=False)
if upload is not None:
    try:
        validate_upload_size(upload.size)
    except ValueError as exc:
        st.warning(str(exc))
        st.stop()
    data, name = upload.getvalue(), upload.name
elif use_sample:
    data = (Path(__file__).parent / "examples" / "messy_sample.csv").read_bytes()
    name = "messy_sample.csv"
else:
    st.info("Choose a CSV above, or explore the sample to see common data quality risks.")
    st.stop()

# Session-only reuse avoids retaining uploaded datasets in a shared global cache.
digest = hashlib.sha256(data).hexdigest()
try:
    if st.session_state.get("dataset_digest") != (digest, PROFILE_VERSION):
        with st.spinner("Checking your dataset…"):
            result = analyze_csv(data, name)
            frame, profile, metadata = result.frame, result.profile, result.metadata
        st.session_state.update(dataset_digest=(digest, PROFILE_VERSION), frame=frame, encoding=metadata.encoding,
                                profile=profile, analysis_metadata=metadata)
        st.session_state.pop("explanations", None)
    frame, encoding, profile = (st.session_state[k] for k in ("frame", "encoding", "profile"))
except (InputValidationError, AnalysisError) as exc:
    st.error("Input/analysis rejected: " + str(exc))
    st.stop()

st.text(f"{name} · decoded as {encoding} · complete-dataset profiling")
s = profile["summary"]
for card, label, value in zip(st.columns(4), ["Rows", "Columns", "Missing cells", "Potential duplicates"],
                              [f"{s['rows']:,}", s["columns"], f"{s['missing_pct']:.2f}%", f"{s['duplicate_pct']:.2f}%"]):
    card.metric(label, value)
counts = s["severity_counts"]
if counts["critical"]:
    st.error(f"{counts['critical']} critical finding(s) require review, regardless of the aggregate score.")
elif counts["high"]:
    st.warning(f"{counts['high']} high-severity finding(s) require review, regardless of the aggregate score.")
else:
    st.write(f"**Review status:** {profile['review_status']}")
for card, label, value in zip(st.columns(5), ["Quality Score / 100", "Critical Issues", "High Issues", "Medium Issues", "Low Issues"],
                              [f"{profile['quality_score']:.0f}", counts["critical"], counts["high"], counts["medium"], counts["low"]]):
    card.metric(label, value)
st.caption("Score summarizes aggregate rule-based signals. Severe local findings may still exist even when the overall score is high. Severity expresses local rule priority, not verified business impact.")
st.caption("Score rounded to whole points for approximate triage; exact arithmetic is retained in the report. Status reflects highest severity. Neither is a percentage of valid data.")
st.caption("Analysis uses parsed values: CSV inference can remove leading zeros and turn NA/null tokens into missing values. Raw-file representation is not preserved.")
for note in profile["context_notes"]:
    st.info(note)
if s["max_missing_column"] is not None:
    st.text(f"Most missing column: {s['max_missing_column']} — {s['max_column_missing_pct']:.2f}% missing")
with st.expander("Missingness by column"):
    st.dataframe(pd.DataFrame([{key: col[key] for key in ("column", "missing_count", "missing_pct")} for col in profile["columns"]]).sort_values("missing_pct", ascending=False), hide_index=True, width="stretch")
with st.expander("How the score is calculated"):
    st.caption("Start at 100 and subtract these heuristic capped penalties. Weights are policy choices, not calibrated estimates. Penalties can overlap; averages can dilute severe column-level findings.")
    st.dataframe(pd.DataFrame(penalty_rows(profile)), hide_index=True, width="stretch")

st.subheader("Review these findings first")
st.caption("Severity orders the list. Ties use issue type and column name, not inferred business impact.")
generate = st.button("Generate AI explanations", disabled=not bool(api_key.strip()) or not bool(profile["issues"]))
if generate:
    with st.spinner("Explaining the computed findings…"):
        st.session_state["explanations"] = explain_profile(profile, api_key.strip(), model.strip(), base_url.strip())
explanations, status = st.session_state.get("explanations", (fallback_explanations(profile), UNAVAILABLE))
st.caption(status)
st.caption("AI-generated guidance" if status.startswith("AI explanations available") else "Built-in rule-based guidance · no generated explanation")
if not any(i["severity"] in ("critical", "high", "medium") for i in profile["issues"]):
    st.success("No medium, high, or critical issues detected by these checks. Review any low-severity findings and domain-specific risks.")
guidance = {x.issue_id: x for x in explanations.issues}
colors = {"critical": "red", "high": "orange", "medium": "blue", "low": "gray"}
for issue in profile["issues"][:5]:
    with st.container(border=True):
        st.badge(issue["severity"].upper(), color=colors[issue["severity"]])
        st.subheader(f"{issue['rank']}. {issue_title(issue)}")
        st.text(f"Affected column: {issue['column'] if issue['column'] is not None else 'Dataset'}")
        st.text("Observed fact: " + observation(issue))
        st.text("Detection rule: " + issue["threshold"])
        st.text("Severity rule: " + issue["severity_rule"])
        st.caption(f"{issue['category'].replace('_', ' ')} · {issue['confidence']}")
        with st.expander("Exact triggering statistic"):
            st.text(trigger(issue))
        item = guidance[issue["issue_id"]]
        st.caption("Generated interpretation. Verify before acting." if status.startswith("AI explanations available") else "Authored rule interpretation")
        st.text(item.explanation)
        st.text("Why it matters: " + item.modeling_impact)
        st.text("Suggested fix: " + item.suggested_fix)
        if issue["issue_type"] in ISSUE_CAVEATS:
            st.caption(ISSUE_CAVEATS[issue["issue_type"]])
with st.expander(f"All {len(profile['issues'])} detected issues"):
    st.dataframe(pd.DataFrame(profile["issues"]), hide_index=True, width="stretch")

explorer, preview = st.tabs(["Column explorer", "Data preview"])
with preview:
    st.dataframe(frame.head(20), width="stretch")
with explorer:
    selected = st.selectbox("Choose a column", options=list(frame.columns))
    p = next(p for p in profile["columns"] if p["column"] == str(selected))
    left, right = st.columns([1, 2])
    with left:
        st.write(f"**Type:** {p['dtype']} · {p['semantic_type']}")
        st.write(f"**Missing:** {p['missing_pct']:.2f}% ({p['missing_count']})")
        st.write(f"**Unique:** {p['unique_count']} · ratio {p['unique_ratio']:.4f}")
        st.write(f"**Date parser success:** {p['datetime_parseability_pct']:.2f}%")
        if p.get("numeric_precision_note"):
            st.warning(p["numeric_precision_note"])
        st.caption("Parser success does not prove the intended date. Ambiguous dates use month-first parsing; two-digit years and bare numbers are excluded. Datetime-like starts at 95% success.")
        if p["semantic_evidence"]:
            with st.expander("Observed parsing mix and examples"):
                st.json(p["semantic_evidence"])
                st.caption("Counts use non-null values after CSV loading. Examples stay local and are not sent to the LLM. Currency and percentage strings are not coerced; numeric-looking strings may be codes.")
        if p.get("raw_representation"):
            with st.expander("Possible representation ambiguity: raw token examples"):
                st.text(f"Observed parsed behavior: {p['dtype']} / {p['semantic_type']}")
                st.json(p["raw_representation"])
                st.caption("CSV inference is heuristic. These bounded pre-inference examples stay in this server session; they are excluded from AI requests and Markdown exports.")
        if p["possible_id"]:
            with st.expander("High-cardinality evidence"):
                st.json(p["id_evidence"])
                st.caption("Name hints and integer-sequence evidence add context only. They do not change the advisory rule or score and cannot establish a key.")
        if p["numeric_stats"]:
            st.dataframe(pd.DataFrame.from_dict(p["numeric_stats"], orient="index", columns=["Value"]), width="stretch")
        with st.expander("Full column profile"):
            st.json(p)
        for issue in profile["issues"]:
            if issue["column"] == str(selected):
                st.badge(issue["severity"].upper(), color=colors[issue["severity"]])
                st.text(f"{issue_title(issue)}: {trigger(issue)}")
    with right:
        chart = None
        if not p["non_null_count"]:
            st.info("No non-null observations to plot. Profiling and report export remain available.")
        elif p["semantic_type"] == "numeric" and not p["finite_count"]:
            st.info("No finite numeric observations to plot. Review the infinite-value finding.")
        elif p["numeric_stats"]:
            values = frame[selected].replace([float("inf"), -float("inf")], float("nan")).dropna()
            chart = px.histogram(x=values, nbins=40, labels={"x": str(selected)}, color_discrete_sequence=["#316be8"])
            st.caption("Finite numeric values · IQR-flagged values may be legitimate, especially in skewed or discrete distributions.")
        else:
            chart = px.bar(x=[item["count"] for item in p["top_values"]],
                           y=[str(item["value"]) for item in p["top_values"]], orientation="h",
                           labels={"x": "Count", "y": str(selected)}, color_discrete_sequence=["#316be8"])
            chart.update_layout(yaxis={"categoryorder": "total ascending"})
            st.caption("Top non-null values · up to 15 categories")
        if chart is not None:
            chart.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(chart, width="stretch")

st.subheader("Take the findings with you")
st.caption(SCOPE_NOTE)
report_key = (digest, PROFILE_VERSION, st.session_state["analysis_metadata"].started_at_utc, explanations.model_dump_json(), status)
if st.session_state.get("report_key") != report_key:
    st.session_state["report_text"] = markdown_report(profile, explanations, status, metadata=st.session_state["analysis_metadata"])
    st.session_state["report_key"] = report_key
st.download_button("Download Markdown report", st.session_state["report_text"],
                   file_name="data_qa_report.md", mime="text/markdown")
