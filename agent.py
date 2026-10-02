"""Bounded model-controlled investigation; deterministic tools own all facts."""
from copy import deepcopy
from dataclasses import asdict
import json
from time import monotonic, perf_counter
from typing import Protocol

from pydantic import ValidationError

from agent_models import Action, DEFAULT_AGENT_LIMITS
from agent_tools import CATALOG, ToolRunner, error
from agent_validator import render_answer, sufficient, validate_selection
from llm import OpenAI
from agent_prompts import PROMPTS


class Planner(Protocol):
    def next_action(self, context: dict) -> dict: ...


class OpenAIPlanner:
    """Small adapter using the existing OpenAI-compatible structured-output API."""
    def __init__(self, api_key, model='gpt-4o-mini', base_url='', *, prompt_version='planner-v2.1', temperature=None):
        self.api_key, self.model, self.base_url = api_key, model, base_url
        self.prompt = PROMPTS[prompt_version]
        self.temperature = temperature
        self.usage = []
        self.provider_error = None

    def next_action(self, context):
        try:
            with OpenAI(api_key=self.api_key, base_url=self.base_url or None, timeout=15, max_retries=0) as client:
                response = client.chat.completions.parse(model=self.model, max_completion_tokens=1800,
                    messages=[{'role': 'system', 'content': self.prompt}, {'role': 'user', 'content': json.dumps(context, allow_nan=False)}],
                    response_format=Action, **({'temperature': self.temperature} if self.temperature is not None else {}))
        except Exception as exc:
            self.provider_error = 'timeout' if 'timeout' in type(exc).__name__.lower() else 'provider_error'
            raise
        usage = getattr(response, 'usage', None)
        self.usage.append({'input_tokens': usage.prompt_tokens, 'output_tokens': usage.completion_tokens} if usage else None)
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError('No structured action')
        return parsed.model_dump()


def investigate(dataframe, question, *, planner=None, api_key='', model='gpt-4o-mini', base_url='', limits=DEFAULT_AGENT_LIMITS):
    """No model means unavailable, never a scripted production fallback.

    An injected Planner is a testing/integration seam. It receives only copied,
    bounded JSON context, never the dataframe or runtime credentials.
    """
    result = {'question': question if isinstance(question, str) else '', 'status': 'failed', 'steps': [], 'tool_calls': [],
              'limits': asdict(limits), 'investigation_version': '2.1',
              'evidence': [], 'answer': '', 'claims': [], 'limitations': [],
              'metrics': {'steps_used': 0, 'tool_calls': 0, 'tool_errors': 0, 'valid_tool_arguments': 0, 'executed_tools': 0,
                          'model_seconds': 0., 'tool_seconds': 0.}}
    metrics = result['metrics']
    started = monotonic()
    reason = 'no model configured; deterministic QA and comparison remain available'
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= 2000:
        reason = 'question must contain between three and two thousand characters'
    elif planner is not None or api_key:
        tool_started = perf_counter()
        try:
            runner = ToolRunner(dataframe, question, limits)
        except Exception:
            runner = None
            reason = 'dataset is outside the supported investigation input boundaries'
        metrics['tool_seconds'] += perf_counter() - tool_started
        if runner is not None:
            planner = planner or OpenAIPlanner(api_key, model, base_url)
            schema = runner.execute('inspect_schema', {})
            metrics['tool_calls'] = metrics['executed_tools'] = metrics['valid_tool_arguments'] = 1
            result['tool_calls'].append({'tool': 'inspect_schema', 'args': {}, 'status': schema['status'], 'executed': True})
            result['steps'].append({'step': 0, 'action': 'tool_call', 'tool': 'inspect_schema', 'status': schema['status']})
            seen = {('inspect_schema', '{}')}
            feedback = None
            selected = None
            reason = 'step limit reached'
            for step in range(1, limits.max_steps + 1):
                if schema['status'] != 'ok':
                    reason = 'schema result exceeds supported limits'
                    break
                if metrics['tool_errors'] >= limits.max_tool_errors:
                    reason = 'error limit reached'
                    break
                if monotonic() - started >= limits.max_seconds:
                    reason = 'elapsed-time budget reached'
                    break
                context = {'question': question, 'schema': schema['values'],
                           'catalog': {name: {'purpose': purpose, 'arguments': cls.model_json_schema()} for name, (cls, purpose) in CATALOG.items()},
                           'evidence': result['evidence'], 'actions': result['steps'], 'last_error': feedback,
                           'remaining_tool_calls': limits.max_tool_calls - metrics['tool_calls']}
                if len(json.dumps(context, ensure_ascii=True, allow_nan=False)) > limits.max_context_chars:
                    reason = 'context budget reached'
                    break
                metrics['steps_used'] = step
                try:
                    model_started = perf_counter()
                    try:
                        raw = planner.next_action(deepcopy(context))
                    finally:
                        metrics['model_seconds'] += perf_counter() - model_started
                    action = Action.model_validate(raw)
                except (ValidationError, ValueError, TypeError):
                    metrics['tool_errors'] += 1
                    feedback = error('invalid_action', 'Use only the action contract; final prose and extra fields are rejected.')
                    result['steps'].append({'step': step, 'action': 'rejected_action', 'error_type': 'invalid_action'})
                    continue
                except Exception:
                    reason = 'model unavailable or timed out'
                    break
                if monotonic() - started >= limits.max_seconds:
                    reason = 'elapsed-time budget reached'
                    break
                if action.action == 'finish':
                    try:
                        if action.tool is not None or action.arguments_json.strip() != '{}':
                            raise ValueError('Finish must not carry tool instructions')
                        chosen = (list(result['evidence']) if action.outcome != 'answer' and not action.evidence_ids
                                  else validate_selection(action.evidence_ids, result['evidence']))
                        if action.outcome == 'answer' and not sufficient(question, chosen):
                            raise ValueError('Missing relevant eligible evidence')
                        selected = chosen
                        result['status'] = 'completed' if action.outcome == 'answer' else 'partial'
                        reason = 'evidence selected' if action.outcome == 'answer' else 'clarification or additional evidence required'
                        result['steps'].append({'step': step, 'action': 'finish', 'status': result['status'], 'evidence_ids': [e['evidence_id'] for e in selected]})
                        break
                    except ValueError:
                        metrics['tool_errors'] += 1
                        feedback = error('insufficient_evidence', 'Final references must exist. Collect relevant eligible evidence; contradictory primary evidence cannot be omitted.')
                        result['steps'].append({'step': step, 'action': 'rejected_finish', 'error_type': 'insufficient_evidence'})
                        continue
                if metrics['tool_calls'] >= limits.max_tool_calls:
                    reason = 'tool-call limit reached'
                    break
                metrics['tool_calls'] += 1
                tool = action.tool
                args = None
                validated = False
                try:
                    args = json.loads(action.arguments_json)
                    if not isinstance(args, dict):
                        raise ValueError('Object required')
                    if tool in CATALOG:
                        typed = CATALOG[tool][0].model_validate(args)
                        args = typed.model_dump()
                        metrics['valid_tool_arguments'] += 1
                        validated = True
                    signature = (tool, json.dumps(args, sort_keys=True, allow_nan=False))
                    if signature in seen:
                        output = error('repeated_call', 'This exact call has already been attempted; use existing evidence or choose a different analysis.')
                    else:
                        seen.add(signature)
                        tool_started = perf_counter()
                        output = runner.execute(tool, args)
                        metrics['tool_seconds'] += perf_counter() - tool_started
                        metrics['executed_tools'] += int(tool in CATALOG)
                except (ValidationError, ValueError, TypeError):
                    output = error('invalid_arguments', 'Provide a valid JSON argument object matching the registered tool schema.')
                record = {'step': step, 'action': 'tool_call', 'tool': tool if tool in CATALOG else '<unregistered>',
                          'args': args if validated else {}, 'status': output['status'], 'executed': output.get('error_type') not in ('repeated_call', 'invalid_arguments', 'unknown_tool')}
                if output['status'] == 'error':
                    metrics['tool_errors'] += 1
                    record['error_type'] = output['error_type']
                    feedback = output
                else:
                    feedback = None
                    eid = f"ev_{len(result['evidence'])+1:02d}"
                    output['evidence_id'] = eid
                    record['evidence_id'] = eid
                    result['evidence'].append(output)
                result['steps'].append(record)
                result['tool_calls'].append(record)
            if result['status'] == 'failed':
                result['status'] = 'partial' if any(e['claims'] for e in result['evidence']) or reason != 'model unavailable or timed out' else 'failed'
            result['answer'], result['claims'] = render_answer(selected if selected is not None else result['evidence'], result['status'], reason)
    if not result['answer']:
        result['answer'], result['claims'] = render_answer([], result['status'], reason)
    result['stop_reason'] = reason
    result['limitations'] = ['No causal or significance inference; no raw-row tools.',
                            'Question interpretation and metric semantics may be incomplete. Inspect exact tool arguments.',
                            'Periods exclude malformed/missing dates; metrics exclude null/non-finite observations.',
                            'Minimum sample size is a heuristic guard, not statistical power or representativeness.']
    metrics['elapsed_seconds'] = round(monotonic() - started, 6)
    return result
