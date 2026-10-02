"""Layer 2: real-provider benchmark capture and deterministic offline evaluation.

No scripted production planner and no LLM judge. Credentials are environment-only.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
from urllib.parse import urlparse
from uuid import uuid4

from agent import OpenAIPlanner, investigate
from agent_models import AgentLimits
from agent_prompts import PROMPTS
from evals.benchmark_scenarios import fixtures, scenarios, select
from evals.investigation import action
from evals.trajectory import SCHEMA_VERSION, compare, evaluate, frame_hash, versions


def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def load(path):
    if path.stat().st_size>100_000_000:
        raise ValueError('Artifact exceeds 100 MB bound')
    def reject(value):
        raise ValueError('Non-finite JSON value')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(path.read_text(encoding='utf-8'),parse_constant=reject,object_pairs_hook=unique)


class FaultProbe:
    """One declared exogenous failure; all subsequent decisions are real-model calls."""
    def __init__(self, planner, injected_call):
        self.planner,self.injected_call,self.used=planner,injected_call,False
    def next_action(self,context):
        if self.injected_call and not self.used:
            self.used=True
            return action(*self.injected_call)
        return self.planner.next_action(context)


def collect(config, cases, frames, output, planner_factory=None):
    config = dict(config, execution='test_double' if planner_factory is not None else 'real_model')
    key=os.getenv('OPENAI_API_KEY','').strip()
    if planner_factory is None and not key:
        raise ValueError('OPENAI_API_KEY is required for real-model benchmarking')
    if (output/'runs.json').exists():
        raise ValueError('Output already contains runs.json; choose a new directory')
    raw=dict(schema_version=SCHEMA_VERSION,benchmark_id=uuid4().hex,started_at=datetime.now(timezone.utc).isoformat(),
             config=config,versions=versions(config['prompt_version']),scenario_contracts=[c.model_dump(mode='json') for c in cases],runs=[])
    write_json(output/'runs.json',raw)
    def one(case, repetition):
        planner=planner_factory(case,repetition) if planner_factory else OpenAIPlanner(key,config['model'],os.getenv('OPENAI_BASE_URL',''),
                    prompt_version=config['prompt_version'],temperature=config['temperature'])
        wrapped=FaultProbe(planner,case.injected_call)
        result=investigate(frames[case.dataset_fixture],case.question,planner=wrapped,
                           limits=AgentLimits(max_steps=config['max_steps'],max_tool_calls=config['max_tool_calls']))
        usage=getattr(planner,'usage',[])
        known=bool(usage) and all(u is not None for u in usage)
        telemetry=dict(input_tokens=sum(u['input_tokens'] for u in usage) if known else None,
                       output_tokens=sum(u['output_tokens'] for u in usage) if known else None,
                       estimated_cost=None,provider_error=getattr(planner,'provider_error',None))
        return dict(run_id=f'{raw["benchmark_id"]}:{case.id}:{repetition}',scenario_id=case.id,repetition=repetition,
                    dataset_hash=frame_hash(frames[case.dataset_fixture]),result=result,telemetry=telemetry,
                    injected_step=1 if case.injected_call else None)
    with ThreadPoolExecutor(max_workers=config['workers']) as pool:
        futures=[pool.submit(one,c,n) for c in cases for n in range(1,config['runs_per_scenario']+1)]
        for future in as_completed(futures):
            run=future.result()
            raw['runs'].append(run)
            raw['runs'].sort(key=lambda r:(config['scenario_ids'].index(r['scenario_id']),r['repetition']))
            write_json(output/'runs.json',raw)
            print(json.dumps({'finished':len(raw['runs']),'expected':len(futures),'scenario':run['scenario_id'],
                              'repetition':run['repetition'],'agent_status':run['result']['status']}),flush=True)
    return raw


def report_markdown(report, regression=None):
    lines=['# Agent behavior benchmark', '',f"Benchmark `{report['benchmark_id']}`; complete: **{report['complete']}**.",
           '',f"Model `{report['config']['model']}`, provider `{report['config']['provider']}`, prompt `{report['config']['prompt_version']}`.",
           '', 'Configuration-specific observations; not universal agent accuracy.', '', '## Overall metrics', '', '| Metric | Mean / rate | Min–max | Stddev | N |', '|---|---:|---|---:|---:|']
    for key,value in report['summary'].items():
        if isinstance(value,dict):
            lines.append(f"| {key} | {value['mean']} | {value['min']} – {value['max']} | {value['stddev']} | {value['n']} |")
        else:
            lines.append(f'| {key} | {value:.4f} | — | — | — |')
    lines+=['','## Failure modes','','| Failure | Runs |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in report['failures'].items()] or ['| None | 0 |']
    lines+=['','## Scenario stability','','| Scenario | Pass / runs | Stability | Path variance | Unstable |','|---|---:|---:|---:|---|']
    for s in report['scenarios']:
        lines.append(f"| {s['scenario_id']} | {s['passed']}/{s['total']} | {s['stability']} | {s['path_variance']} | {s['unstable']} |")
    lines+=['','## Tool usage matrix','','| Scenario | Schema | Time | Segment | Distribution | Quality | Profile | Group |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in report['scenarios']:
        counts=Counter(t for r in report['runs'] if r['scenario_id']==s['scenario_id'] for t in r['tool_path'])
        lines.append('| '+s['scenario_id']+' | '+' | '.join(str(counts[k]) for k in ('schema','time','segment','distribution','quality','profile','group'))+' |')
    lines+=['','## Representative failed trajectories','']
    shown=set()
    for r in report['runs']:
        if not r['success'] and any(f not in shown for f in r['failures']):
            lines += [f"- **{r['scenario_id']}**: {' → '.join(r['tool_path'])}; failures: {', '.join(r['failures'])}; missing: {', '.join(r['missing_evidence']) or 'none' }."]
            shown.update(r['failures'])
    if regression:
        lines+=['','## Regression vs baseline','',f"Passed: **{regression['passed']}**",'']
        lines += ['- Critical: '+m for m in regression['critical']]
        lines += ['- Warning: '+m for m in regression['warnings']]
        lines += [f"- {c['metric']}: {c['baseline']} → {c['current']} (delta {c['delta']})." for c in regression['changes']]
    return '\n'.join(lines)+'\n'


def save_report(output, report, regression=None):
    write_json(output/'summary.json',report)
    write_json(output/'failures.json',[r for r in report['runs'] if not r['success']])
    (output/'runs.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in report['runs']),encoding='utf-8')
    (output/'summary.md').write_text(report_markdown(report,regression),encoding='utf-8')
    if regression:
        write_json(output/'regression.json',regression)


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',default=os.getenv('OPENAI_MODEL') or 'gpt-4o-mini')
    p.add_argument('--prompt-version',choices=list(PROMPTS),default='planner-v2.1')
    p.add_argument('--temperature',type=float,default=None,help='Omit unless supported by the configured model')
    p.add_argument('--runs',type=int,default=3)
    p.add_argument('--workers',type=int,default=3)
    p.add_argument('--suite',choices=['golden','full','safety','recovery','premise'],default='golden')
    p.add_argument('--scenario',action='append',default=[])
    p.add_argument('--category',choices=['direct','multi-step','premise','ambiguous','recovery','adversarial'])
    p.add_argument('--max-scenarios',type=int)
    p.add_argument('--max-steps',type=int,default=8)
    p.add_argument('--max-tool-calls',type=int,default=8)
    p.add_argument('--budgets',help='Small paired budget experiment, e.g. 4,8 (same selected scenarios/repetitions)')
    p.add_argument('--output',type=Path,default=Path('benchmark-results')/datetime.now().strftime('%Y%m%d-%H%M%S'))
    p.add_argument('--offline',type=Path,help='Re-evaluate saved runs.json without a model')
    p.add_argument('--baseline',type=Path,help='Baseline runs.json; independently re-evaluated before comparison')
    p.add_argument('--allow-partial',action='store_true',help='Diagnostic partial report only; cannot pass a regression gate')
    p.add_argument('--list',action='store_true',help='List selected scenarios without any API request')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        cases=select(args.suite,args.scenario,args.category,args.max_scenarios)
        if args.list:
            print(json.dumps([c.model_dump(mode='json') for c in cases],indent=2)); return 0
        if not 1<=args.runs<=100 or not 1<=args.workers<=4 or not 1<=args.max_steps<=20 or not 1<=args.max_tool_calls<=20:
            raise ValueError('Invalid benchmark budget')
        frames=fixtures()
        if args.offline:
            raw=load(args.offline)
            result=evaluate(raw,scenarios(),frames,args.allow_partial)
            regression=compare(evaluate(load(args.baseline),scenarios(),frames),result) if args.baseline else None
            save_report(args.output,result,regression)
            print(json.dumps({'complete':result['complete'],'summary':result['summary'],'failures':result['failures']}))
            return 0 if result['complete'] and (regression is None or regression['passed']) else 2
        budgets=[int(v) for v in args.budgets.split(',')] if args.budgets else [None]
        if len(budgets)>2 or any(b is not None and not 1<=b<=20 for b in budgets):
            raise ValueError('Budget experiment supports one or two budgets from 1 to 20')
        reports=[]
        for budget in budgets:
            output=args.output/f'budget-{budget}' if budget else args.output
            config=dict(model=args.model,provider=urlparse(os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1').hostname,
                        prompt_version=args.prompt_version,temperature=args.temperature,runs_per_scenario=args.runs,workers=args.workers,
                        max_steps=budget or args.max_steps,max_tool_calls=budget or args.max_tool_calls,
                        scenario_ids=[c.id for c in cases],python=platform.python_version(),execution='real_model')
            raw=collect(config,cases,frames,output)
            result=evaluate(raw,scenarios(),frames)
            regression=compare(evaluate(load(args.baseline),scenarios(),frames),result) if args.baseline else None
            save_report(output,result,regression)
            reports.append(result)
            print(json.dumps({'benchmark':result['benchmark_id'],'run_success_rate':result['summary']['run_success_rate'],'failures':result['failures']}))
        if len(reports)==2:
            write_json(args.output/'budget-comparison.json',compare(reports[0],reports[1]))
        # An honest low score is a benchmark result; regression gates determine failure.
        return 0 if regression is None or regression['passed'] else 2
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('Benchmark failed safely: '+type(exc).__name__+'. Check schema, manifest, paths and configuration.',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
