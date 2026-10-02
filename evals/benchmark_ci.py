"""No-network CI: replay the saved synthetic baseline and check pinned scores."""
from pathlib import Path
import json

from evals.agent_benchmark import load
from evals.benchmark_scenarios import fixtures, scenarios
from evals.trajectory import compare, evaluate


def run():
    root=Path(__file__).resolve().parents[1]/'benchmarks/baselines/investigation-v2.2'
    raw=load(root/'runs.json')
    pinned=load(root/'summary.json')
    current=evaluate(raw,scenarios(),fixtures())
    if pinned['benchmark_id']!=current['benchmark_id']:
        raise ValueError('Baseline identity mismatch')
    diff=compare(pinned,current)
    if not diff['passed']:
        raise ValueError('Saved-baseline replay regressed: '+', '.join(diff['critical']))
    experiments = {}
    for path in sorted((root.parents[1]/'results').rglob('runs.json')):
        replay = evaluate(load(path),scenarios(),fixtures())
        if not compare(load(path.with_name('summary.json')),replay)['passed']:
            raise ValueError('Experiment replay changed')
        experiments[path.parent.name] = replay
    candidate = compare(experiments['v22-golden-v21'],experiments['v22-golden-v22'])
    if candidate['passed'] or not any('conversion_device' in reason for reason in candidate['critical']):
        raise ValueError('Known critical-scenario regression was not detected')
    return {'passed':True,'runs':len(current['runs']),'scenarios':len(current['scenarios']),
            'experiment_artifacts_validated':len(experiments),'known_candidate_regression_detected':True,
            'execution':'offline replay; no new model decisions','regression':diff}


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
