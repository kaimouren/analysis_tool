"""Registered deterministic analytics; validated read-only access to one frame."""
from collections import defaultdict
from difflib import get_close_matches
import json
import math
import re
import warnings

import numpy as np
import pandas as pd
from pydantic import ValidationError

from agent_models import (EmptyArgs, ColumnArgs, Scope, MetricArgs, SegmentArgs, GroupArgs,
                          DistributionArgs, DEFAULT_AGENT_LIMITS)
from comparison import compare_datasets
from drift import change, numeric_stats
from ingestion import InputValidationError, serialized_analysis, validate_frame
from qa_core import profile_column, profile_dataframe


CATALOG = {
    'inspect_schema': (EmptyArgs, 'Inspect available columns, observed dtypes and row count; no rows.'),
    'get_dataset_summary': (EmptyArgs, 'Overall missingness and exact duplicate counts.'),
    'profile_column': (ColumnArgs, 'Parsed type, non-null/unique counts, missingness and numeric statistics; no raw examples.'),
    'check_quality': (Scope, 'Compare missingness, duplicates and row counts across explicit periods, or inspect the whole dataset.'),
    'compare_time_periods': (MetricArgs, 'Compare count/sum/mean/median or explicitly binary rate across two non-overlapping periods.'),
    'compare_segments': (SegmentArgs, 'Additive decomposition of period metric change across one/two categorical dimensions; top groups plus Other.'),
    'group_metric': (GroupArgs, 'Aggregate a metric by groups in the whole dataset; optional explicit left-versus-right premise contrast.'),
    'compare_distribution': (DistributionArgs, 'V2 numeric KS or categorical TVD between periods; optional named-category presence check.'),
}


class ToolError(ValueError):
    def __init__(self, kind, message, details=None):
        super().__init__(message)
        self.kind, self.message, self.details = kind, message, details or {}


def error(kind, message, details=None):
    return {'status': 'error', 'error_type': kind, 'message': message, 'recoverable': True, 'details': details or {}}


def _number(value):
    if value is None:
        return 'undefined'
    return str(value) if isinstance(value, int) else format(value, '.8g')


def _name(value):
    return json.dumps(value, ensure_ascii=True)


def claim(kind, text, values):
    return {'claim_type': kind, 'text': text, 'values': values}


def expected_direction(question):
    down = bool(re.search(r'\b(drop\w*|declin\w*|fell|fall\w*|decreas\w*|lower|less)\b|下降|降低|减少', question, re.I))
    up = bool(re.search(r'\b(increas\w*|grew|grow\w*|rise|rose|higher|more|wors\w*|spike\w*)\b|上升|增加|恶化|更高', question, re.I))
    return 'decrease' if down and not up else 'increase' if up and not down else None


def premise(delta, expected, eligible):
    if not eligible or delta is None or expected is None:
        return 'inconclusive'
    return 'supported' if (delta < 0 if expected == 'decrease' else delta > 0) else 'contradicted'


class ToolRunner:
    def __init__(self, dataframe, question='', limits=DEFAULT_AGENT_LIMITS):
        validate_frame(dataframe)
        if len(dataframe.columns) > 80 or any(not isinstance(c, str) or not c.strip() or len(c) > 80 for c in dataframe.columns):
            raise InputValidationError('Investigation supports up to 80 nonblank column names, at most 80 characters each.')
        # Reuse V2 input/scalar/magnitude validation without retaining its profile.
        compare_datasets(dataframe.iloc[:0], dataframe)
        self.frame = dataframe.copy(deep=True)
        self.frame.attrs = {}
        self.question, self.limits = question, limits

    def schema(self):
        return {'rows': len(self.frame), 'columns': [{'name': c, 'dtype': str(self.frame[c].dtype)} for c in self.frame.columns]}

    def _column(self, name):
        if name not in self.frame.columns:
            raise ToolError('missing_column', 'Requested column does not exist; no substitution was made.',
                            {'requested': name[:80], 'suggestions': get_close_matches(name, self.frame.columns, n=3)})

    def _parts(self, args, require_periods=False):
        frame = self.frame
        for f in args.filters:
            self._column(f.column)
            frame = frame[frame[f.column].notna() & frame[f.column].astype(str).eq(f.value)]
        if not len(frame):
            raise ToolError('empty_scope', 'No rows remain in this scope. Inspect the filter or dataset.')
        if args.periods is None:
            if require_periods:
                raise ToolError('missing_periods', 'Specify baseline and current half-open periods with an explicit year.')
            return frame, None, {'scope_rows': len(frame), 'invalid_dates': 0}
        p = args.periods
        self._column(p.time_column)
        boundaries = []
        years = set(re.findall(r'(?<!\d)\d{4}(?!\d)', self.question))
        for text in (p.baseline_start, p.baseline_end, p.current_start, p.current_end):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?', text):
                raise ToolError('invalid_period', 'Use explicit ISO dates or timestamps, with half-open [start, end) boundaries.')
            try:
                t = pd.Timestamp(text)
                t = t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')
                boundaries.append(t)
            except (ValueError, OverflowError):
                raise ToolError('invalid_period', 'Invalid ISO period boundary.') from None
        # Exclusive Jan 1 next-year endpoints are allowed for a stated previous year.
        for index, t in enumerate(boundaries):
            if str(t.year) not in years and not (index in (1, 3) and t.month == t.day == 1 and str(t.year-1) in years):
                raise ToolError('ambiguous_year', 'Specify the year in the question; the agent will not invent it.')
        a, b, c, d = boundaries
        if not a < b <= c < d:
            raise ToolError('invalid_period', 'Periods must be ordered, non-overlapping baseline then current: start < end <= start < end.')
        values = frame[p.time_column]
        native = pd.api.types.is_datetime64_any_dtype(values)
        text = values.astype(str)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            dates = pd.to_datetime(values if native else text.where(text.str.match(r'^\d{4}-\d{2}-\d{2}(?:[ T].*)?$')),
                                   errors='coerce', format='mixed', utc=True)
        invalid = int(dates.isna().sum())
        if dates.notna().sum() == 0:
            raise ToolError('invalid_dates', 'No conservative year-first dates could be parsed in the selected column.')
        left, right = frame[(dates >= a) & (dates < b)], frame[(dates >= c) & (dates < d)]
        if not len(left) or not len(right):
            raise ToolError('empty_period', 'A selected period has no rows. Inspect date coverage and explicit boundaries.',
                            {'baseline_rows': len(left), 'current_rows': len(right), 'invalid_dates': invalid})
        return left, right, {'scope_rows': len(frame), 'invalid_dates': invalid, 'baseline_rows': len(left), 'current_rows': len(right),
                             'boundaries_utc': [t.isoformat() for t in boundaries], 'boundary_rule': '[start, end)'}

    def _metric(self, frame, column, aggregation):
        self._column(column)
        series = frame[column]
        if aggregation == 'count':
            count = int(series.notna().sum())
            return {'value': count, 'valid_count': count, 'rows': len(frame), 'excluded_count': len(frame)-count, 'sum': count}
        if not pd.api.types.is_numeric_dtype(series):
            raise ToolError('wrong_dtype', 'Metric must have a native numeric/bool dtype. Numeric-looking text is not silently coerced.')
        raw = series.dropna()
        values = [v.item() if isinstance(v, np.generic) else v for v in raw if math.isfinite(v)]
        if aggregation == 'rate' and any(v not in (0, 1) for v in values):
            raise ToolError('unsupported_rate', 'Rate requires an explicitly selected binary zero/one or boolean column.')
        total = sum(values) if all(isinstance(v, (int, bool)) for v in values) else math.fsum(sorted(values))
        stats = numeric_stats(values)
        value = (total if values else None) if aggregation == 'sum' else stats['mean'] if aggregation in ('mean', 'rate') else stats['median']
        return {'value': value, 'valid_count': len(values), 'rows': len(frame), 'excluded_count': len(frame)-len(values), 'sum': total}

    def _groups(self, frame, args):
        if len(set(args.segment_columns)) != len(args.segment_columns):
            raise ToolError('invalid_arguments', 'Segment dimensions must be distinct.')
        for column in args.segment_columns:
            self._column(column)
            if column == args.metric_column:
                raise ToolError('invalid_arguments', 'Do not segment by the metric itself.')
        buckets = defaultdict(list)
        display_keys = {}
        for index, row in enumerate(frame[args.segment_columns].itertuples(index=False, name=None)):
            key = tuple(('missing', '') if pd.isna(v) else (type(v).__name__, str(v)) for v in row)
            if any(len(v) > 80 for _, v in key):
                raise ToolError('long_category', 'Category labels exceed the safe output length; choose another dimension.')
            display = tuple(None if k == 'missing' else v for k, v in key)
            if display in display_keys and display_keys[display] != key:
                raise ToolError('ambiguous_categories', 'Distinct typed groups have identical display labels; normalize the dimension explicitly before analysis.')
            display_keys[display] = key
            buckets[key].append(index)
            if len(buckets) > self.limits.max_groups:
                raise ToolError('too_many_groups', 'Too many groups; narrow scope or choose a lower-cardinality dimension.')
        return {key: self._metric(frame.iloc[indices], args.metric_column, args.aggregation) for key, indices in buckets.items()}

    @serialized_analysis
    def execute(self, tool, arguments):
        if tool not in CATALOG:
            return error('unknown_tool', 'Only registered deterministic tools are available.')
        try:
            args = CATALOG[tool][0].model_validate(arguments)
        except (ValidationError, TypeError):
            return error('invalid_arguments', 'Arguments do not match this tool contract; extra fields and executable expressions are not accepted.')
        try:
            values, claims, eligible = self._dispatch(tool, args)
            result = {'status': 'ok', 'tool': tool, 'args': args.model_dump(), 'values': values, 'claims': claims, 'eligible': eligible}
            encoded = json.dumps(result, allow_nan=False, ensure_ascii=True)
            if len(encoded) > self.limits.max_result_chars:
                return error('result_limit', 'Result exceeds the output budget; narrow the selected analysis.')
            return result
        except ToolError as exc:
            return error(exc.kind, exc.message, exc.details)
        except Exception:
            return error('analysis_error', 'This analysis could not complete safely. Choose simpler columns or a narrower scope.')

    def _dispatch(self, tool, args):
        if tool == 'inspect_schema':
            return self.schema(), [], False
        if tool == 'get_dataset_summary':
            summary = profile_dataframe(self.frame)['summary']
            values = {k: summary[k] for k in ('rows', 'columns', 'missing_cells', 'missing_pct', 'duplicate_rows', 'duplicate_pct')}
            return values, [claim('dataset_summary', f"Dataset: {values['rows']} rows; missing cells {_number(values['missing_pct'])}%; exact repeats {_number(values['duplicate_pct'])}%.", values)], bool(len(self.frame))
        if tool == 'profile_column':
            self._column(args.column)
            p = profile_column(self.frame[args.column])
            values = {k: p[k] for k in ('column', 'dtype', 'semantic_type', 'non_null_count', 'unique_count', 'missing_pct', 'numeric_stats')}
            return values, [claim('column_profile', f"Column {_name(args.column)}: {p['non_null_count']} non-null values, {p['unique_count']} distinct values, {_number(p['missing_pct'])}% missing.", values)], p['non_null_count'] >= self.limits.min_sample
        a, b, scope = self._parts(args, require_periods=tool in ('compare_time_periods', 'compare_segments', 'compare_distribution'))
        if tool == 'check_quality':
            if b is None:
                p = profile_dataframe(a)['summary']
                values = {k: p[k] for k in ('rows', 'missing_pct', 'duplicate_pct')}
                return values, [claim('quality', f"Observed missing-cell rate {_number(p['missing_pct'])}%; duplicate rate {_number(p['duplicate_pct'])}%.", values)], len(a) >= self.limits.min_sample
            r = compare_datasets(a, b)
            values = {'scope': scope, 'metrics': r['dataset_metrics'], 'missingness': sorted(
                ({'column': c, **v['missingness']} for c, v in r['columns'].items()),
                key=lambda x: (-abs(x['absolute_change'] or 0), x['column']))[:self.limits.top_groups]}
            claims = []
            eligible = min(len(a), len(b)) >= self.limits.min_sample
            for kind in ('missing_pct', 'duplicate_pct'):
                metric = values['metrics'][kind]
                verdict = premise(metric['absolute_change'], expected_direction(self.question), eligible)
                claims.append(claim('quality_change', f"{kind}: {_number(metric['baseline'])}% → {_number(metric['current'])}%; change {_number(metric['absolute_change'])} percentage points. Directional premise: {verdict}.", {**metric, 'premise': verdict}))
            return values, claims, eligible
        if tool == 'compare_distribution':
            self._column(args.column)
            r = compare_datasets(a[[args.column]], b[[args.column]])['columns'][args.column]
            data = r[args.kind]
            if not data:
                raise ToolError('wrong_dtype', 'Selected distribution method is unavailable for the parsed type.')
            metric = 'ks' if args.kind == 'numeric' else 'tvd'
            eligible = data.get('assessment', data.get('status')) == 'available'
            claims = [claim('distribution', f"{args.kind} distribution for {_name(args.column)}: {metric.upper()} {_number(data[metric])}; descriptive distance only.", {metric: data[metric]})]
            counts = None
            if args.category is not None:
                if args.kind != 'categorical':
                    raise ToolError('invalid_arguments', 'Category presence requires categorical comparison.')
                counts = {'baseline_count': int((a[args.column].notna() & a[args.column].astype(str).eq(args.category)).sum()),
                          'current_count': int((b[args.column].notna() & b[args.column].astype(str).eq(args.category)).sum())}
                claims.append(claim('category_presence', f"Category {_name(args.category)} in {_name(args.column)}: {counts['baseline_count']} baseline rows, {counts['current_count']} current rows. " + ('The current period has no observed rows in this category; a claim of current presence is unsupported.' if not counts['current_count'] else 'Presence alone does not establish a cause.'), counts))
            return {'scope': scope, 'distribution': data, 'category_presence': counts}, claims, eligible
        if tool == 'group_metric':
            if args.periods is not None:
                raise ToolError('invalid_arguments', 'group_metric uses the whole filtered dataset; use compare_segments for two periods.')
            groups = self._groups(a, args)
            records = [{'segment': [None if k == 'missing' else v for k, v in key], **value} for key, value in sorted(groups.items())]
            records.sort(key=lambda r: (-(abs(r['value']) if r['value'] is not None else -1), str(r['segment'])))
            claims = []
            contrast = None
            eligible = bool(records) and all(r['valid_count'] >= self.limits.min_sample for r in records)
            if args.left_value is not None:
                # The questioned group must be explicitly named in the question.
                if not re.search(r'(?<!\w)' + re.escape(args.left_value) + r'(?!\w)', self.question, re.I):
                    raise ToolError('ambiguous_contrast', 'Name the questioned left group explicitly in the question.')
                left = next((r for r in records if r['segment'] == [args.left_value]), None)
                right = next((r for r in records if r['segment'] == [args.right_value]), None)
                if left is None or right is None:
                    raise ToolError('missing_group', 'An explicit contrast group is not observed.')
                delta = change(right['value'], left['value'], 'proportion' if args.aggregation == 'rate' else 'count' if args.aggregation == 'count' else 'metric units')
                eligible = min(left['valid_count'], right['valid_count']) >= self.limits.min_sample
                verdict = premise(delta['absolute_change'], expected_direction(self.question), eligible)
                values = {**delta, 'left': args.left_value, 'right': args.right_value, 'premise': verdict}
                contrast = values
                text = f"Observed {args.aggregation} of {_name(args.metric_column)}: {_name(args.left_value)} {_number(left['value'])}, {_name(args.right_value)} {_number(right['value'])}. Directional premise: {verdict}."
                if verdict == 'contradicted':
                    text += ' The observed data do not support the stated directional premise.'
                claims.append(claim('group_contrast', text, values))
            else:
                for r in sorted(records, key=lambda r: (-(abs(r['value']) if r['value'] is not None else -1), str(r['segment'])))[:self.limits.top_groups]:
                    claims.append(claim('group_metric', f"Group {_name(r['segment'])}: {args.aggregation} {_name(args.metric_column)} = {_number(r['value'])}, valid count {r['valid_count']}.", r))
            return {'groups': records[:self.limits.top_groups], 'total_groups': len(records), 'omitted_groups': max(0, len(records)-self.limits.top_groups), 'contrast': contrast}, claims, eligible
        left, right = self._metric(a, args.metric_column, args.aggregation), self._metric(b, args.metric_column, args.aggregation)
        eligible = min(left['valid_count'], right['valid_count']) >= self.limits.min_sample
        delta = change(left['value'], right['value'], 'proportion' if args.aggregation == 'rate' else 'count' if args.aggregation == 'count' else 'metric units')
        delta['change_pp'] = 100 * delta['absolute_change'] if args.aggregation == 'rate' and delta['absolute_change'] is not None else None
        verdict = premise(delta['absolute_change'], expected_direction(self.question), eligible)
        text = f"{args.aggregation} of {_name(args.metric_column)}: {_number(left['value'])} → {_number(right['value'])}; change {_number(delta['absolute_change'])}"
        text += f"; {_number(delta['change_pp'])} percentage points" if args.aggregation == 'rate' else ''
        text += f". Valid counts {left['valid_count']} → {right['valid_count']}. Directional premise: {verdict}."
        if verdict == 'contradicted':
            text += ' The observed data do not support the stated directional premise.'
        values = {'scope': scope, 'metric': args.metric_column, 'aggregation': args.aggregation, 'baseline': left, 'current': right, 'change': delta, 'premise': verdict}
        claims = [claim('metric_change', text, {**delta, 'premise': verdict})]
        if tool == 'compare_time_periods':
            return values, claims, eligible
        if args.aggregation == 'median':
            raise ToolError('non_additive_metric', 'Median has no additive segment decomposition. Use mean, sum, count or binary rate.')
        if not left['valid_count'] or not right['valid_count']:
            raise ToolError('no_finite_values', 'Both periods require valid metric observations for decomposition.')
        ag, bg = self._groups(a, args), self._groups(b, args)
        if len(set(ag) | set(bg)) > self.limits.max_groups:
            raise ToolError('too_many_groups', 'Combined segment support exceeds the group limit.')
        records = []
        for key in sorted(set(ag) | set(bg)):
            av, bv = ag.get(key), bg.get(key)
            ac, bc = av['sum'] if av else 0, bv['sum'] if bv else 0
            if args.aggregation in ('mean', 'rate'):
                ac, bc = ac / left['valid_count'], bc / right['valid_count']
            difference = bc - ac
            records.append({'segment': [None if k == 'missing' else v for k, v in key], 'is_tail': False,
                            'baseline_count': av['valid_count'] if av else 0, 'current_count': bv['valid_count'] if bv else 0,
                            'baseline_value': av['value'] if av else None, 'current_value': bv['value'] if bv else None,
                            'contribution': difference, 'contribution_pp': difference * 100 if args.aggregation == 'rate' else None,
                            'share_of_net_change_pct': 100 * difference / delta['absolute_change'] if delta['absolute_change'] else None})
        direction = -1 if (delta['absolute_change'] or 0) < 0 else 1
        records.sort(key=lambda r: (-direction * r['contribution'], str(r['segment'])))
        eligible = eligible and all(r[k] == 0 or r[k] >= self.limits.min_sample for r in records for k in ('baseline_count', 'current_count'))
        shown, tail = records[:self.limits.top_groups], records[self.limits.top_groups:]
        if tail:
            shown.append({'segment': [], 'is_tail': True, 'label': 'Other (aggregated tail)', 'groups': len(tail),
                          'contribution': math.fsum(r['contribution'] for r in tail)})
        total = math.fsum(r['contribution'] for r in records)
        if not math.isclose(total, delta['absolute_change'], rel_tol=1e-9, abs_tol=1e-9):
            raise ToolError('unstable_decomposition', 'Segment arithmetic did not reconcile safely; inspect simpler totals.')
        values.update(segments=shown, total_groups=len(records), contribution_sum=total,
                      method='group current sum / current valid total minus group baseline sum / baseline valid total for mean/rate; raw group total difference for sum/count')
        for index, r in enumerate(shown):
            label = 'Other (aggregated tail)' if r['is_tail'] else _name(r['segment'])
            text = f"Segment {label} contributes {_number(r['contribution'])} to the observed aggregate change."
            if not r['is_tail']:
                text += f" Group {args.aggregation}: {_number(r['baseline_value'])} → {_number(r['current_value'])}."
                if r['contribution_pp'] is not None:
                    text += f" Contribution: {_number(r['contribution_pp'])} percentage points."
                if r['share_of_net_change_pct'] is not None:
                    text += f" Share of net observed change: {_number(r['share_of_net_change_pct'])}%."
                if index == 0 and direction * r['contribution'] > 0:
                    text += ' Largest individual contribution in the direction of the aggregate change among the analyzed groups.'
            text += ' This is an arithmetic contribution, not a cause.'
            claims.append(claim('segment_contribution', text, r))
        return values, claims, eligible
