# Deployment readiness and limits

Status: locally runnable and tested; no public deployment or remote GitHub Actions execution is claimed. See `VALIDATION.md` for exact local commands and environments.

## Local setup

Use Python 3.11 and a virtual environment, then install `requirements.txt` and run `python -m streamlit run app.py`. Development verification uses `requirements-dev.txt`, which includes runtime dependencies. No global package installation or API credential is required. `.env.example` is a reference; the application does not load it automatically.

## Streamlit Community Cloud

Publish the reviewed repository to an account you control, select `app.py` as entrypoint and Python 3.11, and deploy using the root `requirements.txt`. `.streamlit/config.toml` sets the upload limit, theme and disabled usage statistics. Follow the [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). This document is a procedure, not evidence that it has been executed publicly.

Keep optional `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `OPENAI_MODEL` in the host secrets mechanism or environment, never in the repository. The default model is configured in `config.py`; provider compatibility is tested only when an actual request runs. Alternate endpoints must be administrator approved; `QA_ALLOWED_LLM_BASE_URLS` is environment-only. If a hosting environment does not support that variable, use the single server-configured endpoint rather than weakening the allowlist. Visitor-selected alternate endpoints additionally require visitor credentials.

## What to disclose to users

- The full CSV reaches the Python hosting server even without AI. Uploads/profiles remain in application session memory, not deliberately written to disk; host swap, telemetry and crash dumps are outside that guarantee.
- Optional AI sends allowlisted aggregate metrics, penalty totals and anonymous top-five issue fields. Aggregates can still be sensitive. Provider retention depends on the provider/account.
- CSV parsing can remove leading zeros and reinterpret NA/null/boolean/numeric tokens. This is exploratory screening, not a contract asserting source fidelity or business correctness.
- Headline scores are rounded policy indicators. A critical finding can coexist with a score near 100.

## Resource limits and admission

10 MiB encoded CSV, 200,000 rows, 200 columns, 2 million cells, 256 MiB deep frame memory, and 65,536 characters per text cell. CSV's standard parser also has an independent field ceiling; V1.1 does not mutate that process-global setting. Native finite numeric magnitudes over 1e150 are rejected for numerical safety. No existing size limit was increased.

These are per-input guardrails, not a process memory limit. The decoded string, parsed frame, intermediates, Streamlit session data, chart serialization and report can coexist. Analyses within one process are serialized to protect Python 3.11 warning-filter state; waiting sessions still retain uploads and frames. There is no admission queue bound, cancellation policy, per-user quota or host-level concurrency limit. Read [CONCURRENCY.md](CONCURRENCY.md) before exposing the app broadly.

For serious hosting, establish a measured memory budget, authenticated admission, request limits, timeouts/cancellation, provider quotas and a defined retention policy. Process isolation is a candidate if parallel CPU work is required; it is not implemented here. Do not derive a user-capacity guarantee from a ten-thread synthetic probe. A shared server API key allows visitors to spend the administrator's provider budget; omit it for a public demonstration.

## Acceptance procedure

Install into a clean virtual environment; run `python -m pip check`, `python -m pytest -q`, `python -m ruff check .`, `python evals/run.py`, `python evals/behavioral.py`, and `python evals/stress.py`. Run benchmarks on the intended host. Launch without a key, upload a clean CSV, the problematic fixture, malformed input and an oversized field; download the Markdown report. Confirm logs contain only approved fields. Test actual secret/provider configuration separately if enabling AI.

CI is configured for dependency consistency, tests, lint, synthetic regression, behavioral coverage and score stress. Local execution of those commands is evidence about this environment. It is not a substitute for an actual remote workflow or host smoke test. No Docker, authentication, database or distributed infrastructure was added to imply readiness beyond these checks.


## V1.2 publication status and exact manual steps

**GitHub repository/remote Actions: Not verified.** There is no configured remote, GitHub CLI, GitHub token environment variable or usable noninteractive GitHub credential in this environment. No remote repository was created or overwritten. **Public Streamlit deployment: Not verified.** No deployment connector or authenticated Community Cloud deployment session was available. There is no tested public URL.

The tracked V1.2 snapshot removes developer-specific absolute paths from historical command examples. Local Git history still contains earlier machine-path examples; it has not been destructively rewritten. Publish the history-free release source archive instead of pushing that historical local repository unchanged. The archive contains tracked files only, not virtual environments, local credentials, private runtime folders or Git history.

After authenticating on your own machine, these steps publish the reviewed source without carrying local history:

1. Extract `.release/data-qa-agent-v1.2.0.zip` into a new empty directory and open that directory in a terminal.
2. Run the Quickstart and all test/eval commands from README before publication.
3. Run `git init -b main`, `git add .`, and `git commit -m "Release Data QA Agent V1.2.0"`.
4. Run `gh auth login` and `gh auth status`. Check whether `OWNER/data-qa-agent` already exists with `gh repo view OWNER/data-qa-agent`. Replace OWNER with your intended account. If it exists, stop and choose another name or explicitly review that repository; do not overwrite it.
5. For an unused repository name, run `gh repo create data-qa-agent --public --source . --remote origin --description "Deterministic-first CSV health checks with transparent scoring and optional LLM explanations." --push`.
6. Run `gh run list --workflow tests.yml`, then `gh run watch RUN_ID --exit-status` and `gh run view RUN_ID --log`. Confirm the push triggered a run, dependency installation/checks succeeded, and every test/lint/evaluation step passed. Record the actual run URL. A configured workflow alone is not evidence.
7. At Community Cloud, choose Create app, select the repository and `main`, set `app.py` as the entrypoint, and explicitly choose Python 3.11 in Advanced settings. Leave provider secrets empty for the first public smoke test.
8. Deploy and test the actual assigned public URL: initial load, no-key mode, messy sample, clean CSV, chart, report download, layout, malformed input and absence of path/secret errors. Only then add the tested public URL to README and the workflow/deployment results to VALIDATION.md.

If enabling a provider, place supported settings in Advanced settings / Secrets; never commit the secret file. A public server key permits unmetered visitor spending in this app, so prefer no server key for a portfolio demo. Source examples remain on the hosting server/session, not on the client alone.

The Community Cloud procedure and secret placement were checked against the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [secrets documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management). These instructions do not claim remote execution.
