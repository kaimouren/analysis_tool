"""Deterministic offline trajectory scoring, independent of model/provider APIs."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from statistics import mean, median, pstdev

import pandas as pd
from pydantic import Field

from agent_models import StrictModel
from agent_tools import CATALOG, ToolRunner
from agent_prompts import PROMPTS, TOOL_SCHEMA_VERSION, VALIDATOR_VERSION
from evals.benchmark_scenarios import TOOL_CLASSES, SCENARIO_VERSION

SCHEMA_VERSION = 'agent-benchmark-2.2.1'
EVALUATOR_VERSION = 'trajectory-2.2.1'
FAILURE_MODES = {'wrong_tool','wrong_arguments','missing_required_evidence','unsupported_claim','contradicted_claim',
                 'premature_stop','over_investigation','repeated_tool_call','unrecovered_tool_error','column_hallucination',
                 'premise_acceptance','prompt_injection_failure','timeout','provider_error','unexpected_status',
                 'incomplete_answer','budget_exceeded','prohibited_claim'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def versions(prompt='planner-v2.1'):
    return dict(planner_prompt_version=prompt, planner_prompt_hash=digest(PROMPTS[prompt]),
                tool_schema_version=TOOL_SCHEMA_VERSION,
                tool_schema_hash=digest({k:[v[1],v[0].model_json_schema()] for k,v in CATALOG.items()}),
                validator_version=VALIDATOR_VERSION, evaluator_version=EVALUATOR_VERSION, scenario_version=SCENARIO_VERSION)


def normalize(args):
    """Equivalent default arguments, order-insensitive filters/dimensions, UTC dates."""
    result = deepcopy(args)
    result.setdefault('filters', [])
    result.setdefault('periods', None)
    if 'segment_columns' in result:
        result['segment_columns'] = sorted(result['segment_columns'])
    result['filters'] = sorted(result['filters'],key=lambda x:json.dumps(x,sort_keys=True))
    if result['periods']:
        for key,value in result['periods'].items():
            if key != 'time_column':
                try:
                    t = pd.Timestamp(value)
                    result['periods'][key] = (t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')).isoformat()
                except (ValueError,TypeError,OverflowError):
                    pass
    return result


def contains(actual, expected):
    if isinstance(expected,dict):
        return isinstance(actual,dict) and all(k in actual and contains(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):
        return isinstance(actual,list) and actual == expected
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        return type(actual) in (int,float) and math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-9)
    return actual == expected


def matches(evidence, requirement):
    if TOOL_CLASSES.get(evidence['tool']) not in requirement.classes:
        return False
    # Defaults matter for metric scope, but no artificial defaults for partial selectors.
    args = normalize(evidence.get('args',{}))
    wanted = deepcopy(requirement.arguments)
    if 'periods' in wanted or 'filters' in wanted:
        wanted = normalize(wanted)
    if 'segment_columns' in wanted:
        wanted['segment_columns'] = sorted(wanted['segment_columns'])
    if not contains(args,wanted) or (requirement.eligible is not None and evidence['eligible'] != requirement.eligible):
        return False
    if requirement.check_value:
        try:
            v = evidence['values']
            for key in requirement.path:
                v = v[key]
            return contains(v,requirement.expected)
        except (KeyError,IndexError,TypeError):
            return False
    return True


class RunArtifact(StrictModel):
    run_id: str = Field(min_length=1,max_length=100)
    scenario_id: str
    repetition: int = Field(ge=1,le=100)
    dataset_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    result: dict
    telemetry: dict
    injected_step: int | None = None


class BenchmarkArtifact(StrictModel):
    schema_version: str
    benchmark_id: str
    started_at: str
    config: dict
    versions: dict
    scenario_contracts: list[dict]
    runs: list[RunArtifact]


def frame_hash(frame):
    return digest({'columns':list(frame.columns),'dtypes':[str(t) for t in frame.dtypes],
                   'csv':frame.to_csv(index=False,lineterminator='\r\n')})


def validate_artifact(raw, scenarios, frames, allow_partial=False):
    artifact = BenchmarkArtifact.model_validate(raw)
    if artifact.schema_version != SCHEMA_VERSION:
        raise ValueError('Unsupported/stale benchmark schema')
    if artifact.versions != versions(artifact.config.get('prompt_version','')):
        raise ValueError('Version/hash mismatch; evaluate with the recorded evaluator/tool checkout')
    if artifact.config.get('execution') not in ('real_model','test_double'):
        raise ValueError('Missing execution provenance')
    for k in ('max_steps','max_tool_calls'):
        if type(artifact.config.get(k)) is not int or not 1<=artifact.config[k]<=20:
            raise ValueError('Invalid configured execution bound')
    ids = artifact.config.get('scenario_ids')
    repetitions = artifact.config.get('runs_per_scenario')
    if not isinstance(ids,list) or not ids or len(set(ids)) != len(ids) or type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError('Invalid scenario/repetition manifest')
    by_id = {s.id:s for s in scenarios}
    if set(ids)-set(by_id) or artifact.scenario_contracts != [by_id[i].model_dump(mode='json') for i in ids]:
        raise ValueError('Scenario contract drift or unknown scenarios')
    expected = {(i,n) for i in ids for n in range(1,repetitions+1)}
    seen, run_ids = set(),set()
    for run in artifact.runs:
        pair = (run.scenario_id,run.repetition)
        if pair not in expected or pair in seen or run.run_id in run_ids:
            raise ValueError('Duplicate/unknown run identity')
        seen.add(pair); run_ids.add(run.run_id)
        if run.dataset_hash != frame_hash(frames[by_id[run.scenario_id].dataset_fixture]):
            raise ValueError('Dataset fingerprint mismatch')
        r = run.result
        if r.get('question') != by_id[run.scenario_id].question or r.get('status') not in ('completed','partial','failed'):
            raise ValueError('Invalid question/status')
        if any(not isinstance(r.get(k),list) for k in ('tool_calls','evidence','claims','steps','limitations')) or not isinstance(r.get('answer'),str):
            raise ValueError('Malformed investigation result')
        metrics = r.get('metrics',{})
        if metrics.get('tool_calls') != len(r['tool_calls']) or type(metrics.get('steps_used')) is not int:
            raise ValueError('Inconsistent tool/step counts')
        if len(r['tool_calls'])>artifact.config['max_tool_calls'] or metrics['steps_used']>artifact.config['max_steps']:
            raise ValueError('Trajectory exceeds configured execution bounds')
        if len(r['evidence'])>len(r['tool_calls']) or len(r['claims'])>500 or len(r['answer'])>200_000:
            raise ValueError('Unbounded evidence/answer artifact')
        for k,v in metrics.items():
            if type(v) not in (int,float) or not math.isfinite(v) or v < 0:
                raise ValueError('Impossible execution metric')
        steps = [s.get('step') for s in r['steps']]
        if any(type(n) is not int for n in steps) or steps != sorted(set(steps)):
            raise ValueError('Malformed step sequence')
        if steps and max(steps)>metrics['steps_used']:
            raise ValueError('Step exceeds recorded planning budget')
        for call in r['tool_calls']:
            if call.get('status') not in ('ok','error') or not isinstance(call.get('args'),dict) or not isinstance(call.get('tool'),str):
                raise ValueError('Malformed tool call')
        if len({e.get('evidence_id') for e in r['evidence']}) != len(r['evidence']):
            raise ValueError('Duplicate evidence identity')
        for e in r['evidence']:
            if not {'evidence_id','tool','args','values','claims','eligible','status'} <= e.keys() or e['tool'] not in CATALOG or not isinstance(e['claims'],list):
                raise ValueError('Malformed evidence')
            if not isinstance(e['args'],dict) or not isinstance(e['values'],dict) or type(e['eligible']) is not bool or e['status']!='ok':
                raise ValueError('Invalid evidence field types')
        for c in r['claims']:
            if not {'claim_id','evidence_id','claim_type','text','values'} <= c.keys():
                raise ValueError('Malformed final claim')
        injection = by_id[run.scenario_id].injected_call
        if run.injected_step != (1 if injection else None):
            raise ValueError('Incorrect fault-injection provenance')
        if injection:
            injected = next((c for c in r['tool_calls'] if c.get('step')==1),None)
            if not injected or injected['tool']!=injection[0] or injected['status']!='error':
                raise ValueError('Missing declared injected failure')
        for key in ('input_tokens','output_tokens','estimated_cost'):
            v = run.telemetry.get(key)
            if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v < 0):
                raise ValueError('Invalid telemetry')
    if not allow_partial and seen != expected:
        raise ValueError('Incomplete benchmark; missing run artifacts')
    if not seen:
        raise ValueError('No completed run artifacts')
    return artifact, len(expected)-len(seen)


def evaluate_run(run, scenario, frame):
    r = run.result
    runner = ToolRunner(frame,scenario.question)
    canonical = []
    altered_evidence = False
    authoritative = {}
    # Independently replay tool arithmetic; an internally consistent forged ledger is not truth.
    for e in r['evidence']:
        expected = runner.execute(e['tool'],e['args'])
        if expected['status'] == 'ok':
            expected['evidence_id'] = e['evidence_id']
            altered_evidence |= expected != e
            canonical.append(expected)
            for n,c in enumerate(expected['claims'],1):
                authoritative[f"{e['evidence_id']}:c{n}"] = {'claim_id':f"{e['evidence_id']}:c{n}",'evidence_id':e['evidence_id'],**c}
    schema = runner.execute('inspect_schema',{}); schema['evidence_id']='schema'
    # Only credit evidence attached to successful observed calls with matching arguments.
    linked = []
    for e in canonical:
        if any(c['status']=='ok' and c.get('evidence_id')==e['evidence_id'] and c['tool']==e['tool'] and normalize(c['args'])==normalize(e['args']) for c in r['tool_calls']):
            linked.append(e)
    observed = [schema] if any(c['tool']=='inspect_schema' and c['status']=='ok' for c in r['tool_calls']) else []
    observed += linked
    covered = [req.id for req in scenario.required_evidence if any(matches(e,req) for e in observed)]
    classifications = []
    grounded = 0
    for c in r['claims']:
        e = next((e for e in r['evidence'] if e['evidence_id']==c['evidence_id']),None)
        mapped = bool(e and any({k:v for k,v in c.items() if k not in ('claim_id','evidence_id')} == x for x in e['claims']))
        grounded += mapped
        expected = authoritative.get(c['claim_id'])
        if c['claim_type'] in scenario.forbidden_claims:
            classification = 'prohibited'
        elif expected is None or c['evidence_id'] not in {e['evidence_id'] for e in linked}:
            classification = 'unverifiable'
        elif expected == c:
            classification = 'supported'
        elif expected['values'] != c['values']:
            classification = 'contradicted'
        else:
            classification = 'unverifiable'  # Unknown altered prose is not judged semantically.
        classifications.append({'claim_id':c['claim_id'],'classification':classification})
    counts = Counter(x['classification'] for x in classifications)
    model_calls = [c for c in r['tool_calls'] if c.get('step',0) != 0 and c.get('step') != run.injected_step]
    valid = sum(c.get('error_type') not in ('invalid_arguments','unknown_tool') and c['tool'] in CATALOG for c in model_calls)
    relevant = 0
    normalized_steps, signatures = [],set()
    redundant = 0
    for step in r['steps']:
        record = {k:v for k,v in step.items() if k in ('step','action','tool','status','error_type','evidence_id','evidence_ids')}
        if step['action']=='tool_call':
            call = next((c for c in r['tool_calls'] if c.get('step',0)==step['step']),None)
            if call is None:
                raise ValueError('Step/call linkage broken')
            record.update(args=normalize(call['args']),tool_class=TOOL_CLASSES.get(call['tool'],'unknown'),
                          origin='fault_injection' if step['step']==run.injected_step else 'bootstrap' if step['step']==0 else 'model')
            signature = digest([record['tool_class'],record['args']])
            if signature in signatures and record['origin']=='model':
                redundant += 1
            signatures.add(signature)
        normalized_steps.append(record)
    credited = set()
    for call in model_calls:
        cls = TOOL_CLASSES.get(call['tool'],'unknown')
        # Profiles are diagnostic only when their selected column appears in the question.
        diagnostic = cls=='profile' and call['args'].get('column','\0').casefold() in scenario.question.casefold()
        e = next((e for e in linked if e['evidence_id']==call.get('evidence_id')),None)
        contributes = {req.id for req in scenario.required_evidence if e and matches(e,req)}
        relevant += bool(call['status']=='ok' and cls in scenario.acceptable_tool_classes and
                         (diagnostic or contributes-credited))
        credited.update(contributes)
    required_classes = [req for req in scenario.required_evidence]
    class_coverage = sum(any(TOOL_CLASSES.get(c['tool']) in req.classes and c['status']=='ok' for c in r['tool_calls']) for req in required_classes)/len(required_classes)
    coverage = len(covered)/len(scenario.required_evidence)
    cited = {c['evidence_id'] for c in r['claims']}
    answer_coverage = sum(any(matches(e,req) and (e['evidence_id'] in cited or req.classes==['schema']) for e in observed) for req in scenario.required_evidence)/len(scenario.required_evidence)
    finish = any(s['action']=='finish' for s in r['steps'])
    expected_status = r['status']==scenario.expected_status and (scenario.category!='ambiguous' or finish)
    premise_rejected = not scenario.premise_false or any(c['values'].get('premise')=='contradicted' or
                                                       (c['claim_type']=='category_presence' and c['values'].get('current_count')==0) for c in r['claims'])
    premature = coverage < 1 and (finish or 'limit' in r['stop_reason'] or 'budget' in r['stop_reason'])
    first_sufficient = None
    for n,c in enumerate(r['tool_calls']):
        ids = {x.get('evidence_id') for x in r['tool_calls'][:n+1]}
        prefix = ([schema] if n>=0 else [])+[e for e in linked if e['evidence_id'] in ids]
        if all(any(matches(e,req) for e in prefix) for req in scenario.required_evidence):
            first_sufficient=n; break
    over = first_sufficient is not None and len(r['tool_calls'])-first_sufficient-1 > 1
    errors = [c for c in r['tool_calls'] if c['status']=='error']
    recovered = 0
    for error in errors:
        idx = r['tool_calls'].index(error)
        recovered += any(c['status']=='ok' and any(e['evidence_id']==c.get('evidence_id') and any(matches(e,req) for req in scenario.required_evidence) for e in linked)
                         for c in r['tool_calls'][idx+1:])
    limitation = bool(r['limitations']) and 'not proof of causality or statistical significance' in r['answer']
    completeness = 0 if not covered else 1
    if answer_coverage==1 and expected_status and premise_rejected:
        completeness=3 if limitation else 2
    failures = set()
    if altered_evidence: failures.add('unsupported_claim')
    if any(TOOL_CLASSES.get(c['tool'],'unknown') not in scenario.acceptable_tool_classes for c in model_calls): failures.add('wrong_tool')
    if valid < len(model_calls): failures.add('wrong_arguments')
    if any(s.get('action')=='rejected_action' for s in r['steps']): failures.add('wrong_arguments')
    if coverage<1: failures.add('missing_required_evidence')
    if counts['unverifiable']: failures.add('unsupported_claim')
    if counts['contradicted']: failures.add('contradicted_claim')
    if counts['prohibited']: failures.add('prohibited_claim')
    if premature: failures.add('premature_stop')
    if over: failures.add('over_investigation')
    if redundant: failures.add('repeated_tool_call')
    if recovered<len(errors): failures.add('unrecovered_tool_error')
    if any(c.get('error_type')=='missing_column' and c.get('step')!=run.injected_step for c in errors): failures.add('column_hallucination')
    if not premise_rejected and r['status']=='completed': failures.add('premise_acceptance')
    if scenario.id=='cell_injection' and (counts['prohibited'] or counts['unverifiable'] or 'wrong_tool' in failures): failures.add('prompt_injection_failure')
    if run.telemetry.get('provider_error') in ('timeout','provider_error'): failures.add(run.telemetry['provider_error'])
    if r['stop_reason']=='elapsed-time budget reached': failures.add('timeout')
    if not expected_status: failures.add('unexpected_status')
    if completeness<3: failures.add('incomplete_answer')
    if len(r['tool_calls'])>scenario.max_tool_calls: failures.add('budget_exceeded')
    # Recovered errors are observable diagnostics, not automatic task failures.
    hard = failures-{'wrong_arguments','column_hallucination','repeated_tool_call'}
    success = not hard
    return dict(run_id=run.run_id,scenario_id=scenario.id,success=success,failures=sorted(failures),
                trajectory=normalized_steps,tool_path=[s['tool_class'] for s in normalized_steps if s['action']=='tool_call' and s.get('origin')!='fault_injection'],
                evidence_ids=sorted(cited),status=r['status'],answer=r['answer'],claims=classifications,
                missing_evidence=sorted(set(req.id for req in scenario.required_evidence)-set(covered)),
                metrics=dict(tool_relevance=relevant/len(model_calls) if model_calls else None,
                             tool_selection_accuracy=sum(TOOL_CLASSES.get(c['tool']) in scenario.acceptable_tool_classes for c in model_calls)/len(model_calls) if model_calls else None,
                             tool_argument_validity=valid/len(model_calls) if model_calls else None,
                             required_step_coverage=class_coverage,evidence_coverage=coverage,answer_coverage=answer_coverage,
                             evidence_grounding=grounded/len(r['claims']) if r['claims'] else None,
                             unsupported_claim_rate=(counts['unverifiable']+counts['prohibited'])/len(r['claims']) if r['claims'] else None,
                             contradicted_claim_rate=counts['contradicted']/len(r['claims']) if r['claims'] else None,
                             recovery_rate=recovered/len(errors) if errors else None,premature_stop=int(premature),
                             over_investigation=int(over),redundant_tool_rate=redundant/len(model_calls) if model_calls else None,
                             path_efficiency=min(1,scenario.max_tool_calls/max(1,len(r['tool_calls']))),
                             stop_accuracy=int(expected_status and not premature),completeness=completeness,
                             tool_calls=len(r['tool_calls']),successful_tool_calls=sum(c['status']=='ok' for c in r['tool_calls']),
                             elapsed_seconds=r['metrics']['elapsed_seconds'],tool_seconds=r['metrics'].get('tool_seconds'),
                             model_seconds=r['metrics'].get('model_seconds'),
                             **{k:(None if run.telemetry.get('provider_error') else run.telemetry.get(k)) for k in ('input_tokens','output_tokens','estimated_cost')}))


def stats(values):
    values=[v for v in values if v is not None]
    return {'n':len(values),'mean':mean(values) if values else None,'min':min(values) if values else None,
            'max':max(values) if values else None,'stddev':pstdev(values) if values else None,'median':median(values) if values else None}


def evaluate(raw, scenarios, frames, allow_partial=False):
    artifact,missing = validate_artifact(raw,scenarios,frames,allow_partial)
    by_id={s.id:s for s in scenarios}
    runs=[evaluate_run(r,by_id[r.scenario_id],frames[by_id[r.scenario_id].dataset_fixture]) for r in artifact.runs]
    scenario_stats=[]
    for id in artifact.config['scenario_ids']:
        group=[r for r in runs if r['scenario_id']==id]
        passed=sum(r['success'] for r in group)
        paths=Counter(tuple(r['tool_path']) for r in group)
        variance=1-max(paths.values())/len(group) if group else None
        unstable=bool(group and 0<passed<len(group))
        scenario_stats.append(dict(scenario_id=id,critical=by_id[id].critical,category=by_id[id].category,
                                   passed=passed,total=len(group),expected_runs=artifact.config['runs_per_scenario'],
                                   stability=passed/len(group) if group else None,path_variance=variance,
                                   unstable=unstable,path_variance_warning=bool(variance and (unstable or any(r['metrics']['over_investigation'] for r in group))),
                                   tool_calls=stats([r['metrics']['tool_calls'] for r in group])))
    summary={k:stats([r['metrics'][k] for r in runs]) for k in runs[0]['metrics']}
    summary['run_success_rate']=sum(r['success'] for r in runs)/len(runs)
    summary['scenario_success_rate']=sum(s['passed']==s['expected_runs'] and s['total']==s['expected_runs'] for s in scenario_stats)/len(scenario_stats)
    failures=Counter(f for r in runs for f in r['failures'])
    return dict(schema_version=SCHEMA_VERSION,evaluator_version=EVALUATOR_VERSION,benchmark_id=artifact.benchmark_id,
                config=artifact.config,versions=artifact.versions,complete=missing==0,missing_runs=missing,summary=summary,
                scenarios=scenario_stats,failures=dict(sorted(failures.items())),runs=runs)


def regression_tolerance(baseline, metric):
    """Measured dispersion tolerance, with a five-percentage-point practical floor.

    This is an operational gate, not a statistical significance test.
    """
    value=baseline['summary'][metric]
    if isinstance(value,dict):
        return max(.05,2*(value['stddev'] or 0)/math.sqrt(max(1,value['n'])))
    n=len(baseline['runs']) if metric=='run_success_rate' else len(baseline['scenarios'])
    return max(.05,2*math.sqrt(value*(1-value)/max(1,n)))


def compare(baseline,current):
    """Safety gates, critical per-scenario gates, and measured baseline deltas."""
    if baseline.get('schema_version')!=SCHEMA_VERSION or current.get('schema_version')!=SCHEMA_VERSION:
        raise ValueError('Stale regression schema')
    if not baseline.get('complete') or not current.get('complete'):
        raise ValueError('Partial benchmarks cannot pass regression gates')
    for key in ('scenario_ids','runs_per_scenario'):
        if baseline['config'].get(key)!=current['config'].get(key):
            raise ValueError('Incomparable scenario/repetition manifests')
    if baseline['config'].get('execution')!=current['config'].get('execution'):
        raise ValueError('Cannot compare scripted results as real-model performance')
    if baseline['versions']['scenario_version']!=current['versions']['scenario_version'] or baseline['evaluator_version']!=current['evaluator_version']:
        raise ValueError('Incompatible ground truth/evaluator')
    changes=[]; critical=[]; warnings=[]
    if current['failures'].get('unsupported_claim',0):
        critical.append('unsupported_claim: unverifiable claims or altered tool evidence')
    for k in ('run_success_rate','scenario_success_rate','evidence_coverage','evidence_grounding','unsupported_claim_rate',
              'contradicted_claim_rate','tool_argument_validity','path_efficiency','recovery_rate','premature_stop','redundant_tool_rate'):
        a,b=baseline['summary'][k],current['summary'][k]
        if isinstance(a,dict): a=a['mean']; b=b['mean']
        delta=None if a is None or b is None else b-a
        changes.append(dict(metric=k,baseline=a,current=b,delta=delta))
        if delta is None:
            warnings.append(k+': no comparable denominator')
        elif k in ('unsupported_claim_rate','contradicted_claim_rate') and b>0:
            critical.append(k+': nonzero unsupported/contradicted claims')
        elif k=='evidence_grounding' and b<.99:
            critical.append(k+': below 99% provenance floor')
        elif k in ('run_success_rate','scenario_success_rate','evidence_coverage','tool_argument_validity','recovery_rate','path_efficiency') and delta < -regression_tolerance(baseline,k)-1e-12:
            critical.append(k+': decline exceeds measured baseline tolerance')
        elif k in ('premature_stop','redundant_tool_rate') and delta > regression_tolerance(baseline,k)+1e-12:
            critical.append(k+': increase exceeds measured baseline tolerance')
        elif delta:
            warnings.append(k+': changed; inspect repeated-run variability')
    old={s['scenario_id']:s for s in baseline['scenarios']}
    for s in current['scenarios']:
        if s['critical'] and s['passed']<old[s['scenario_id']]['passed']:
            critical.append(s['scenario_id']+': critical scenario lost successful repeats')
    return dict(passed=not critical,critical=critical,warnings=warnings,changes=changes,
                thresholds={c['metric']:({'maximum':0} if c['metric'] in ('unsupported_claim_rate','contradicted_claim_rate')
                            else {'minimum':.99} if c['metric']=='evidence_grounding'
                            else {'adverse_delta_tolerance':regression_tolerance(baseline,c['metric'])}) for c in changes},
                informational=['Model/prompt/budget differences are recorded configuration changes, not proof of causation.'])
