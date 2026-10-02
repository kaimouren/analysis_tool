"""Evaluator red-team tests: score behavior, not an artifact's self-reported score."""
from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from agent import investigate
from evals.agent_benchmark import collect, load, main, save_report
from evals.benchmark_scenarios import Requirement, Scenario, TOOL_CLASSES, fixtures, scenarios, select
from evals.investigation import ScriptedPlanner, metric
from evals.trajectory import SCHEMA_VERSION, compare, evaluate, frame_hash, matches, normalize, versions


@pytest.fixture(scope='module')
def frames():
    return fixtures()


def case(id='conversion_device'):
    return next(c for c in scenarios() if c.id==id)


def artifact(frames, id='conversion_device', calls=None, outcome='answer', repeats=1):
    s=case(id)
    if calls is None:
        calls=[('compare_time_periods',metric()),('compare_segments',metric(segment_columns=['device']))]
    runs=[]
    for n in range(1,repeats+1):
        r=investigate(frames[s.dataset_fixture],s.question,planner=ScriptedPlanner(calls,outcome))
        runs.append(dict(run_id=f'{id}:{n}',scenario_id=id,repetition=n,dataset_hash=frame_hash(frames[s.dataset_fixture]),
                         result=r,telemetry={'input_tokens':None,'output_tokens':None,'estimated_cost':None,'provider_error':None},
                         injected_step=1 if s.injected_call else None))
    return dict(schema_version=SCHEMA_VERSION,benchmark_id='test',started_at='2026-10-02T00:00:00Z',
                config=dict(model='test-double',provider='offline',execution='test_double',prompt_version='planner-v2.1',
                            scenario_ids=[id],runs_per_scenario=repeats,max_steps=8,max_tool_calls=8),
                versions=versions(),scenario_contracts=[s.model_dump(mode='json')],runs=runs)


def score(raw,frames):
    return evaluate(raw,scenarios(),frames)


def test_scenario_schema_and_suites():
    cases=scenarios()
    assert len(cases)==36 and len(select('golden'))==12
    assert len({c.id for c in cases})==36
    assert all(sum(c.category==cat for c in cases)==6 for cat in {c.category for c in cases})
    for suite in ('full','golden','safety','premise','recovery'):
        assert select(suite)
    with pytest.raises(ValueError): select(ids=['invented'])
    with pytest.raises(ValueError): select(maximum=0)
    with pytest.raises(ValidationError): Scenario.model_validate({**cases[0].model_dump(),'max_tool_calls':0})
    with pytest.raises(ValidationError): Scenario.model_validate({**cases[0].model_dump(),'required_evidence':[]})


def test_ground_truth_numeric_contracts(frames):
    from agent_tools import ToolRunner
    reverse={v:k for k,v in TOOL_CLASSES.items()}; reverse['quality']='check_quality'
    for s in scenarios():
        runner=ToolRunner(frames[s.dataset_fixture],s.question)
        for req in s.required_evidence:
            if req.arguments:
                output=runner.execute(reverse[req.classes[0]],req.arguments)
                assert output['status']=='ok' and matches(output,req),(s.id,req.id)


def test_normalization_dates_filter_order_and_segments():
    a=metric(segment_columns=['device','country'],filters=[dict(column='country',value='US'),dict(column='device',value='mobile')])
    b=deepcopy(a); b['segment_columns'].reverse(); b['filters'].reverse()
    b['periods']['baseline_start']='2024-02-01T00:00:00Z'
    assert normalize(a)==normalize(b)
    assert normalize({})==normalize({'filters':[],'periods':None})


def test_complete_answer_and_alternative_tool_classes(frames):
    r=score(artifact(frames),frames)
    assert r['summary']['run_success_rate']==1
    assert r['summary']['evidence_coverage']['mean']==1
    assert r['summary']['completeness']['mean']==3
    req=Requirement(id='alternative',classes=['time','segment'],arguments={'metric_column':'conversion'})
    raw=artifact(frames)
    assert matches(raw['runs'][0]['result']['evidence'][1],req)


def test_grounded_but_incomplete_is_failure(frames):
    raw=artifact(frames,calls=[('compare_time_periods',metric())],outcome='insufficient')
    r=score(raw,frames)
    assert r['summary']['evidence_grounding']['mean']==1
    assert r['summary']['evidence_coverage']['mean']==.5
    assert r['summary']['run_success_rate']==0
    assert r['failures']['missing_required_evidence']==1 and r['failures']['premature_stop']==1


def test_wrong_scope_does_not_cover_correct_fact(frames):
    raw=artifact(frames,calls=[('compare_time_periods',metric()),('compare_segments',metric(segment_columns=['country']))])
    r=score(raw,frames)
    assert r['summary']['evidence_coverage']['mean']==.5
    assert r['summary']['tool_relevance']['mean']==.5


def test_redundant_equivalent_calls_and_recovery(frames):
    raw=artifact(frames,calls=[('compare_time_periods',metric()),('compare_time_periods',{**metric(),'filters':[]}),
                              ('compare_segments',metric(segment_columns=['device']))])
    r=score(raw,frames)
    assert r['summary']['redundant_tool_rate']['mean']==pytest.approx(1/3)
    assert r['summary']['recovery_rate']['mean']==1
    assert r['failures']['repeated_tool_call']==1


def test_over_investigation(frames):
    raw=artifact(frames,calls=[('compare_time_periods',metric()),('compare_segments',metric(segment_columns=['device'])),
                              ('profile_column',{'column':'revenue'}),('get_dataset_summary',{})])
    r=score(raw,frames)
    assert r['summary']['over_investigation']['mean']==1
    assert not r['runs'][0]['success']


@pytest.mark.parametrize('kind', ['contradicted','unverifiable','prohibited'])
def test_claim_classification_replays_arithmetic(frames,kind):
    raw=artifact(frames)
    c=raw['runs'][0]['result']['claims'][0]
    ledger=raw['runs'][0]['result']['evidence'][0]['claims'][0]
    if kind=='contradicted':
        c['values']['absolute_change']=999
        ledger['values']['absolute_change']=999  # consistent forged ledger still fails independent replay
    elif kind=='unverifiable':
        c['text']='A fabricated explanation without a tool-authored counterpart'
        ledger['text']=c['text']
    else:
        c['claim_type']='significance'; ledger['claim_type']='significance'
    report=score(raw,frames)
    assert report['runs'][0]['claims'][0]['classification']==kind
    assert report['summary']['run_success_rate']==0


def test_recovery_fault_is_disclosed_and_not_counted_as_model_selection(frames):
    raw=artifact(frames,'recover_missing_column',calls=[('compare_time_periods',metric(column='conversions')),
                                                      ('compare_time_periods',metric()),('compare_segments',metric(segment_columns=['device']))])
    r=score(raw,frames)
    assert r['summary']['recovery_rate']['mean']==1
    assert r['summary']['tool_argument_validity']['mean']==1
    assert any(s.get('origin')=='fault_injection' for s in r['runs'][0]['trajectory'])


def test_provider_timeout_is_not_successful_cautious_answer(frames):
    raw=artifact(frames,calls=[],outcome='insufficient')
    raw['runs'][0]['telemetry']['provider_error']='timeout'
    report=score(raw,frames)
    assert report['failures']['timeout']==1
    assert report['summary']['run_success_rate']==0


def test_repeated_run_stability_and_path_variance(frames):
    raw=artifact(frames,repeats=3)
    partial=artifact(frames,calls=[('compare_time_periods',metric())],outcome='insufficient')
    raw['runs'][1]['result']=partial['runs'][0]['result']
    r=score(raw,frames)
    assert r['summary']['run_success_rate']==pytest.approx(2/3)
    assert r['summary']['scenario_success_rate']==0
    s=r['scenarios'][0]
    assert s['unstable'] and s['stability']==pytest.approx(2/3)
    assert s['path_variance']==pytest.approx(1/3)


def test_harmless_path_variation_not_automatically_failure(frames):
    raw=artifact(frames,repeats=2)
    longer=artifact(frames,calls=[('profile_column',{'column':'conversion'}),('compare_time_periods',metric()),
                                 ('compare_segments',metric(segment_columns=['device']))])
    raw['runs'][1]['result']=longer['runs'][0]['result']
    r=score(raw,frames)
    assert r['scenarios'][0]['path_variance']==.5
    assert not r['scenarios'][0]['path_variance_warning']
    assert r['summary']['run_success_rate']==1


@pytest.mark.parametrize('mutation',['missing_run','duplicate_id','bad_schema','mixed_prompt','metric_nan','negative_calls','bad_steps',
                                   'bad_hash','changed_contract','unknown_run','duplicate_evidence','bad_telemetry'])
def test_malformed_artifacts_fail_safely(frames,mutation):
    raw=artifact(frames,repeats=2)
    if mutation=='missing_run': raw['runs'].pop()
    if mutation=='duplicate_id': raw['runs'][1]['run_id']=raw['runs'][0]['run_id']
    if mutation=='bad_schema': raw['schema_version']='old'
    if mutation=='mixed_prompt': raw['versions']['planner_prompt_version']='planner-v2.2'
    if mutation=='metric_nan': raw['runs'][0]['result']['metrics']['elapsed_seconds']=float('nan')
    if mutation=='negative_calls': raw['runs'][0]['result']['metrics']['tool_calls']=-1
    if mutation=='bad_steps': raw['runs'][0]['result']['steps'][1]['step']=0
    if mutation=='bad_hash': raw['runs'][0]['dataset_hash']='0'*64
    if mutation=='changed_contract': raw['scenario_contracts'][0]['critical']=False
    if mutation=='unknown_run': raw['runs'][0]['scenario_id']='unknown'
    if mutation=='duplicate_evidence': raw['runs'][0]['result']['evidence'].append(raw['runs'][0]['result']['evidence'][0])
    if mutation=='bad_telemetry': raw['runs'][0]['telemetry']['input_tokens']=-1
    with pytest.raises((ValueError,ValidationError,KeyError)):
        score(raw,frames)


def test_partial_report_explicit_and_not_regression_eligible(frames):
    raw=artifact(frames,repeats=2); raw['runs'].pop()
    partial=evaluate(raw,scenarios(),frames,allow_partial=True)
    assert not partial['complete'] and partial['missing_runs']==1
    with pytest.raises(ValueError): compare(partial,partial)


def test_baseline_gate_pass_and_critical_failure(frames):
    baseline=score(artifact(frames,repeats=3),frames)
    assert compare(baseline,baseline)['passed']
    raw=artifact(frames,repeats=3)
    raw['runs'][0]['result']=artifact(frames,calls=[],outcome='insufficient')['runs'][0]['result']
    current=score(raw,frames)
    diff=compare(baseline,current)
    assert not diff['passed']
    assert any('critical scenario' in s for s in diff['critical'])


def test_safety_regression_cannot_hide_behind_aggregate_improvement(frames):
    baseline=score(artifact(frames),frames)
    current=deepcopy(baseline)
    current['summary']['run_success_rate']=1
    current['summary']['unsupported_claim_rate']['mean']=.01
    assert not compare(baseline,current)['passed']


@pytest.mark.parametrize('change',['schema','manifest','repetitions','evaluator'])
def test_incompatible_baselines_rejected(frames,change):
    base=score(artifact(frames),frames); current=deepcopy(base)
    if change=='schema': current['schema_version']='old'
    if change=='manifest': current['config']['scenario_ids']=['other']
    if change=='repetitions': current['config']['runs_per_scenario']=2
    if change=='evaluator': current['evaluator_version']='old'
    with pytest.raises(ValueError): compare(base,current)


def test_offline_roundtrip_and_reports(frames,tmp_path):
    raw=artifact(frames)
    path=tmp_path/'runs.json'; path.write_text(json.dumps(raw),encoding='utf-8')
    first=score(raw,frames); second=score(load(path),frames)
    assert first==second
    save_report(tmp_path/'report',second,compare(first,second))
    text=(tmp_path/'report/summary.md').read_text(encoding='utf-8')
    assert 'Tool usage matrix' in text and 'Regression vs baseline' in text
    assert main(['--offline',str(path),'--baseline',str(path),'--output',str(tmp_path/'cli')])==0
    assert main(['--offline',str(path),'--baseline',str(tmp_path/'missing.json')])==2


def test_loader_rejects_duplicate_keys_and_nonfinite(tmp_path):
    path=tmp_path/'bad.json'
    for content in ('{"x":1,"x":2}','{"x":NaN}'):
        path.write_text(content)
        with pytest.raises(ValueError): load(path)


def test_no_credentials_no_fake_benchmark(monkeypatch,frames,tmp_path):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    assert main(['--max-scenarios','1','--output',str(tmp_path)])==2
    assert not (tmp_path/'runs.json').exists()
    assert main(['--suite','golden','--list'])==0


def test_collect_test_double_provenance_and_missing_usage(frames,tmp_path):
    c=case()
    config=dict(model='test-double',provider='offline',execution='test_double',prompt_version='planner-v2.1',temperature=None,
                runs_per_scenario=2,workers=1,max_steps=8,max_tool_calls=8,scenario_ids=[c.id])
    raw=collect(config,[c],frames,tmp_path,lambda c,n:ScriptedPlanner([('compare_time_periods',metric()),('compare_segments',metric(segment_columns=['device']))]))
    assert len(raw['runs'])==2 and raw['config']['execution']=='test_double'
    assert all(r['telemetry']['input_tokens'] is None for r in raw['runs'])
    assert score(raw,frames)['summary']['run_success_rate']==1
    with pytest.raises(ValueError): collect(config,[c],frames,tmp_path,lambda c,n:None)


def test_forged_tool_values_cannot_pass_even_with_unchanged_claims(frames):
    raw=artifact(frames)
    raw['runs'][0]['result']['evidence'][0]['values']['premise']='supported by imaginary data'
    report=score(raw,frames)
    assert not report['runs'][0]['success']
    assert report['failures']['unsupported_claim']==1


def test_execution_layers_cannot_be_compared_as_same_population(frames):
    base=score(artifact(frames),frames)
    other=deepcopy(base); other['config']['execution']='real_model'
    with pytest.raises(ValueError): compare(base,other)


def test_ambiguous_error_limit_is_not_successful_clarification(frames):
    from evals.investigation import action
    class Spam:
        def next_action(self,context):
            return action('inspect_schema',{})
    s=case('ambiguous_dates')
    raw=artifact(frames,id=s.id,calls=[],outcome='clarify')
    raw['runs'][0]['result']=investigate(frames[s.dataset_fixture],s.question,planner=Spam())
    assert score(raw,frames)['summary']['run_success_rate']==0


def test_prohibited_claim_triggers_nonzero_unsupported_gate(frames):
    base=score(artifact(frames),frames)
    raw=artifact(frames); raw['runs'][0]['result']['claims'][0]['claim_type']='causal_effect'
    report=score(raw,frames)
    assert report['summary']['unsupported_claim_rate']['mean']>0
    assert not compare(base,report)['passed']


@pytest.mark.parametrize('key,value',[('max_steps',0),('max_tool_calls',1000)])
def test_artifact_cannot_disable_execution_bounds(frames,key,value):
    raw=artifact(frames); raw['config'][key]=value
    with pytest.raises(ValueError): score(raw,frames)


def test_claimless_success_is_not_fabricated_perfect_grounding(frames):
    raw=artifact(frames,id='missing_year',calls=[],outcome='clarify')
    report=score(raw,frames)
    assert report['summary']['run_success_rate']==1
    assert report['summary']['evidence_grounding']['mean'] is None
    assert report['summary']['tool_selection_accuracy']['mean'] is None


def test_unknown_final_request_usage_is_not_counted_as_complete(frames):
    raw=artifact(frames)
    raw['runs'][0]['telemetry'].update(input_tokens=123,output_tokens=4,provider_error='timeout')
    report=score(raw,frames)
    assert report['summary']['input_tokens']['mean'] is None


def test_observation_instrumentation_preserves_production_prompt():
    from agent_prompts import PROMPTS
    from agent import OpenAIPlanner
    assert OpenAIPlanner('test').prompt==PROMPTS['planner-v2.1']
    assert PROMPTS['planner-v2.2'].startswith(PROMPTS['planner-v2.1'])


def test_fixture_hash_uses_explicit_platform_independent_line_endings(frames,monkeypatch):
    import pandas as pd
    original=pd.DataFrame.to_csv
    observed=[]
    def wrapped(self,*args,**kwargs):
        observed.append(kwargs.get('lineterminator'))
        return original(self,*args,**kwargs)
    monkeypatch.setattr(pd.DataFrame,'to_csv',wrapped)
    frame_hash(frames['base'])
    assert observed==['\r\n']
