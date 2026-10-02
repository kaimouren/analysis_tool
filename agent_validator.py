"""Evidence selection validation and code-authored final claims, not prose regex."""
import re


PRIMARY = {'metric_change', 'quality_change', 'quality', 'group_contrast', 'distribution', 'category_presence'}


def validate_selection(evidence_ids, evidence):
    available = {e['evidence_id'] for e in evidence}
    if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids) or set(evidence_ids) - available:
        raise ValueError('Final selection must reference existing, distinct evidence IDs.')
    # Primary/contradictory results cannot be cherry-picked out of the answer.
    required = {e['evidence_id'] for e in evidence if any(c['claim_type'] in PRIMARY for c in e['claims'])}
    return [e for e in evidence if e['evidence_id'] in set(evidence_ids) | required]


def sufficient(question, evidence):
    kinds = {c['claim_type'] for e in evidence if e['eligible'] for c in e['claims']}
    q = question.casefold()
    metric_requested = bool(re.search(r'\b(conversion|revenue|retention|churn|average|aov)\b|转化|收入|留存|流失', q))
    if any(word in q for word in ('missing', 'duplicate', 'quality', '缺失', '重复', '质量')):
        temporal = bool(re.search(r'\b(after|before|versus|compared|spike|wors\w*)\b|恶化|之后|相比', q))
        quality_ok = 'quality_change' in kinds if temporal else bool(kinds & {'quality', 'quality_change'})
        if not quality_ok or not metric_requested:
            return quality_ok
    if any(word in q for word in ('categor', 'composition', 'disappear', 'distribution', '类别', '分布')):
        return bool(kinds & {'distribution', 'category_presence'})
    if 'group_contrast' in kinds:
        return True
    if 'metric_change' not in kinds:
        return False
    primary = [e for e in evidence if e['tool'] == 'compare_time_periods' and e['eligible']]
    # The first eligible period comparison anchors the investigated metric.
    # A later, unrelated contradicted metric cannot shortcut its explanation.
    if primary and primary[0]['values'].get('premise') == 'contradicted':
        return True
    if re.search(r'\b(why|segment|accounts|explain|drove)\b|为什么|分组|解释', q):
        # A decomposition must actually correspond to the primary metric/scope.
        segments = [e for e in evidence if e['tool'] == 'compare_segments' and e['eligible']]
        return any(all(p['args'].get(k) == s['args'].get(k) for k in ('metric_column', 'aggregation', 'periods', 'filters'))
                   for p in primary[:1] for s in segments)
    return bool(primary)


def render_answer(evidence, status, reason):
    selected = []
    for e in evidence:
        for n, c in enumerate(e['claims'], 1):
            selected.append({'claim_id': f"{e['evidence_id']}:c{n}", 'evidence_id': e['evidence_id'], **c})
    lines = [f"[{c['evidence_id']}] {c['text']}" for c in selected]
    if not lines:
        lines = ['Insufficient evidence to answer this question.']
    if status != 'completed':
        lines.insert(0, f'Investigation {status}: {reason}. Findings below are incomplete.')
    lines += ['These are observed associations and arithmetic comparisons, not proof of causality or statistical significance.',
              'The model selected tools and evidence; the factual statements above were rendered by code. Review the interpreted columns, scope and aggregation.']
    return '\n\n'.join(lines), selected
