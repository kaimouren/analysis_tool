"""Markdown presentation shared by UI and notebook use."""
from datetime import datetime, timezone
import json

from llm import fallback_explanations
from presentation import SCOPE_NOTE, ISSUE_CAVEATS, issue_title, observation, penalty_rows
from events import emit
from models import AnalysisMetadata
from policy import APP_VERSION


def escape(value):
    text = str(value).replace("\n", " ").replace("\r", " ")
    for char in "\\`*_{}[]<>|#":
        text = text.replace(char, "\\" + char)
    return text


def trigger(issue):
    return f"{issue['stat']} = {issue['value']} (trigger: {issue['threshold']})"


def markdown_report(profile, explanations=None, status="Deterministic guidance", *, metadata: AnalysisMetadata | None = None):
    """Create a standalone audit report; timestamps never affect the QA profile."""
    authored = fallback_explanations(profile, limit=None)
    explanations = explanations or authored
    guidance = {item.issue_id: item for item in authored.issues}
    guidance.update({item.issue_id: item for item in explanations.issues})
    generated_ids = {item.issue_id for item in explanations.issues} if status.startswith("AI explanations available") else set()
    s = profile["summary"]
    lines = ["# Data QA report", "", SCOPE_NOTE, "",
             "Statistics and score are deterministic; the LLM only explains results.",
             "", f"Review status: {escape(profile['review_status'])}",
             f"Profile version: {profile['profile_version']}; score policy: {profile['score_policy_version']}",
             f"Application version: {APP_VERSION}",
             f"Report generated UTC: {datetime.now(timezone.utc).isoformat()}",
             f"Analysis started UTC: {metadata.started_at_utc if metadata else 'Not supplied (direct profile API)'}",
             f"Analysis duration (seconds): {metadata.duration_seconds if metadata else 'Not supplied'}",
             "", f"- Rows: {s['rows']}", f"- Columns: {s['columns']}",
             f"- Missing cells: {s['missing_cells']} ({s['missing_pct']:.4f}%)",
             f"- Potential duplicate rows (exact repeats after first): {s['duplicate_rows']} ({s['duplicate_pct']:.4f}%)",
             f"- Quality score (approximate policy indicator): {profile['quality_score']:.0f}/100",
             f"- Exact policy arithmetic (not calibrated precision): {profile['quality_score']}/100",
             "- Local issue counts: " + "; ".join(f"{level}: {s['severity_counts'][level]}" for level in ("critical", "high", "medium", "low")),
             "Score summarizes aggregate rule-based signals. Severe local findings may still exist even when the overall score is high.",
             "", "This score is an uncalibrated summary of these rules, not a percentage of valid data. A high score can coexist with critical findings.", ""]
    lines.extend(escape(note) for note in profile["context_notes"])
    lines.extend(["", "## Score penalties", ""])
    lines.extend(f"- {row['Category']}: {row['Penalty']} / cap {row['Cap']}. {row['Reason for policy']}" for row in penalty_rows(profile))
    lines.extend(["", "Penalties can overlap; they are not independent errors. Averaging across cells and columns can dilute severe local findings."])
    lines.extend(["", "Generated interpretation. Verify before acting." if generated_ids else "Authored score interpretation.",
                  "", escape(explanations.score_explanation), "", escape(status), "", "## Methodology", "",
                  "All parsed rows are profiled, with no cleaning or statistical sampling. Only representation examples in the local UI are sampled; those raw-token examples are excluded from this export. Exact repeats are counted after the first occurrence. Missingness uses pandas nulls; string-format warnings are separate, advisory and unscored. IQR percentages use finite numeric observations. Severity is policy-based; confidence describes observation versus interpretation, not a calibrated probability.",
                  "", "Effective thresholds (for reproduction):", "", "```json", json.dumps(profile["thresholds"], indent=2), "```", "",
                  "## Issue summary", ""])
    lines.extend(f"- {level}: {sum(i['severity'] == level for i in profile['issues'])}" for level in ("critical", "high", "medium", "low"))
    lines.extend(["", "## Detailed findings (ranked)", ""])
    if not profile["issues"]:
        lines.append("No issues detected by the documented checks. This does not establish fitness for a specific model.")
    for issue in profile["issues"]:
        item = guidance[issue["issue_id"]]
        lines.extend([f"### {issue['rank']}. {issue_title(issue)} — {issue['severity']}", "",
                      f"Affected column: {escape(issue['column']) if issue['column'] is not None else 'Dataset'}",
                      f"Category: {issue['category']}; confidence: {escape(issue['confidence'])}",
                      "", f"Observed fact: {escape(observation(issue))}", "", escape(trigger(issue)), "",
                      f"Severity rule: {escape(issue['severity_rule'])}", "",
                      "Structured evidence:", "", "```json", json.dumps(issue['evidence'], indent=2), "```", "",
                      "Interpretation (AI-generated):" if issue["issue_id"] in generated_ids else "Interpretation (authored rule guidance):",
                      "Generated interpretation. Verify before acting." if issue["issue_id"] in generated_ids else "",
                      "", escape(item.explanation), "",
                      f"Modeling impact: {escape(item.modeling_impact)}", "",
                      f"Suggested fix: {escape(item.suggested_fix)}", ""])
        if issue["issue_type"] in ISSUE_CAVEATS:
            lines.extend([escape(ISSUE_CAVEATS[issue["issue_type"]]), ""])
    lines.extend(["## Column missingness", ""])
    lines.extend(f"- {escape(p['column'])}: {p['missing_count']} missing ({p['missing_pct']:.4f}%)" for p in profile["columns"])
    lines.extend(["## All detected issues", ""])
    lines.extend(f"- {i['severity']} / {issue_title(i)} / {escape(i['column'] if i['column'] is not None else 'Dataset')}: {escape(trigger(i))}; severity rule: {escape(i['severity_rule'])}" for i in profile["issues"])
    lines.extend(["", "No cleaning was applied. Analysis uses parsed values: CSV inference can normalize numeric types, leading zeros and NA/null tokens; this is not raw-file fidelity. Score formula and limitations are documented in README.md."])
    lines.extend(["", "## Limitations", "", SCOPE_NOTE,
                  "Weights and thresholds are uncalibrated. Correlated findings can overlap; aggregate scores can dilute local defects. Parser success does not prove meaning. Duplicate entity identifiers are not checked without a declared key. LLM prose is interpretation and can be wrong."])
    emit("report_generated", issue_count=len(profile["issues"]))
    return "\n".join(lines)
