"""Optional bounded real-provider smoke on synthetic data; never runs in pytest.

Uses explicitly configured environment credentials. Up to eight requests, no
retries. Print only outcome/observed tool names, never credentials or errors.
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import investigate
from agent_models import AgentLimits
from investigation_ui import investigation_sample


def main():
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        print('SKIPPED: no API key; live investigation remains unverified.')
        return 0
    result = investigate(investigation_sample(), 'Why did conversion drop in March 2024 compared with February 2024? Use binary rate and segment by device and country.',
                         api_key=key, model=os.getenv('OPENAI_MODEL') or 'gpt-4o-mini', base_url=os.getenv('OPENAI_BASE_URL', ''),
                         limits=AgentLimits(max_steps=8, max_tool_calls=8, max_tool_errors=3, max_seconds=120))
    ok = result['status'] == 'completed' and any(e['tool'] == 'compare_segments' for e in result['evidence'])
    print(json.dumps(dict(passed=ok, status=result['status'], stop_reason=result['stop_reason'], metrics=result['metrics'],
                          tools=[c['tool'] for c in result['tool_calls']],
                          steps=[{k: v for k, v in s.items() if k != 'args'} for s in result['steps']])))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
