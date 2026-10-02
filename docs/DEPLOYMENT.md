# Deployment readiness and limits

Status: V2.2 source and the portfolio README are published at [kaimouren/analysis_tool](https://github.com/kaimouren/analysis_tool). The README's local commit `84b7624` was applied to the existing publication history as `4f8582c`, with identical tracked file trees. No history was rewritten. Public Streamlit deployment remains **Not verified**. See [validation evidence](../VALIDATION.md); the original publication notes below are historical.

## Local setup

V2.2 uses the same Python 3.11 entrypoint and dependencies. All three modes are available in `app.py`. Without a model key, investigation displays configuration guidance and disables execution; QA and comparison remain usable. Leave `QA_HISTORY_PATH` unset on public Streamlit deployments; setting it enables shared server-local metadata history without user isolation. For a trusted local installation, set it to `.qa-history/comparisons.sqlite3` before starting Streamlit. The variable is environment-only; no visitor can select a filesystem path. Cloud-local files are not a durable storage guarantee.

V2 acceptance additionally runs `python evals/comparison.py`. Smoke-test baseline/current uploads, direction, no-key guidance, comparison report download and stale-result removal after changing inputs. Two uploads and their intermediates coexist, so do not infer hosting capacity from V1's single-frame measurements.

Use Python 3.11 and a virtual environment, then install `requirements.txt` and run `python -m streamlit run app.py`. Development verification uses `requirements-dev.txt`, which includes runtime dependencies. No global package installation or API credential is required. `.env.example` is a reference; the application does not load it automatically.

## Streamlit Community Cloud

Publish the reviewed repository to an account you control, select `app.py` as entrypoint and Python 3.11, and deploy using the root `requirements.txt`. `.streamlit/config.toml` sets the upload limit, theme and disabled usage statistics. Follow the [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). This document is a procedure, not evidence that it has been executed publicly.

Keep optional `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `OPENAI_MODEL` in the host secrets mechanism or environment, never in the repository. The default model is configured in `config.py`; provider compatibility is tested only when an actual request runs. Alternate endpoints must be administrator approved; `QA_ALLOWED_LLM_BASE_URLS` is environment-only. If a hosting environment does not support that variable, use the single server-configured endpoint rather than weakening the allowlist. Visitor-selected alternate endpoints additionally require visitor credentials.

## What to disclose to users

- The full CSV reaches the Python hosting server even without AI. Uploads/profiles remain in application session memory, not deliberately written to disk; host swap, telemetry and crash dumps are outside that guarantee.
- Optional QA/comparison explanations send allowlisted aggregates and anonymous fields. Investigation additionally sends the question, real schema names/types, selected group labels, and bounded evidence after consent. Aggregates can still be sensitive. Provider retention depends on the provider/account.
- CSV parsing can remove leading zeros and reinterpret NA/null/boolean/numeric tokens. This is exploratory screening, not a contract asserting source fidelity or business correctness.
- Headline scores are rounded policy indicators. A critical finding can coexist with a score near 100.

## Resource limits and admission

10 MiB encoded CSV, 200,000 rows, 200 columns, 2 million cells, 256 MiB deep frame memory, and 65,536 characters per text cell. CSV's standard parser also has an independent field ceiling; V1.1 does not mutate that process-global setting. Native finite numeric magnitudes over 1e150 are rejected for numerical safety. No existing size limit was increased.

These are per-input guardrails, not a process memory limit. The decoded string, parsed frame, intermediates, Streamlit session data, chart serialization and report can coexist. Analyses within one process are serialized to protect Python 3.11 warning-filter state; waiting sessions still retain uploads and frames. There is no admission queue bound, cancellation policy, per-user quota or host-level concurrency limit. Read [CONCURRENCY.md](CONCURRENCY.md) before exposing the app broadly.

For serious hosting, establish a measured memory budget, authenticated admission, request limits, timeouts/cancellation, provider quotas and a defined retention policy. Process isolation is a candidate if parallel CPU work is required; it is not implemented here. Do not derive a user-capacity guarantee from a ten-thread synthetic probe. A shared server API key allows visitors to spend the administrator's provider budget; omit it for a public demonstration.

## Acceptance procedure

Install into a clean virtual environment; run `python -m pip check`, `python -m pytest -q`, `python -m ruff check .`, `python evals/run.py`, `python evals/behavioral.py`, and `python evals/stress.py`. Run benchmarks on the intended host. Launch without a key, upload a clean CSV, the problematic fixture, malformed input and an oversized field; download the Markdown report. Confirm logs contain only approved fields. Test actual secret/provider configuration separately if enabling AI.

CI is configured for dependency consistency, tests, lint, synthetic regression, behavioral coverage and score stress. Local execution of those commands is evidence about this environment. It is not a substitute for an actual remote workflow or host smoke test. No Docker, authentication, database or distributed infrastructure was added to imply readiness beyond these checks.


## Original V1.2 publication status and manual procedure (historical)

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

## Deploy the published repository

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with access to `kaimouren/analysis_tool`.
2. Choose **Create app**, then **Yup, I have an app**. Enter repository `kaimouren/analysis_tool`, branch `main`, and file path `app.py`.
3. In **Advanced settings**, explicitly select **Python 3.11**. Root `requirements.txt` supplies runtime dependencies.
4. Leave **Secrets empty**. Do not configure a shared `OPENAI_API_KEY` or `QA_HISTORY_PATH`. `.env` is not loaded automatically. The committed `.streamlit/config.toml` sets the upload limit and disables usage statistics.
5. Save settings and deploy. Inspect build/startup logs. Dependencies use bounded version ranges rather than a complete lockfile, so host installation is a separate check from local validation.
6. Open the assigned URL in a fresh browser session. Test Single Dataset QA with the sample and a small CSV, a Markdown download, baseline/current comparison and its download, and investigation's no-key guidance/disabled button. Check malformed input for safe errors and absence of local paths or debug traces.
7. Open a second independent session and confirm the first session's uploaded data is not visible. Keep history disabled. This smoke test does not establish a general tenant-isolation guarantee.
8. Only after these checks succeed, record the actual public URL and add it to README. GitHub publication and successful Actions do not themselves deploy Streamlit.

During portfolio finalization, no Streamlit deployment connector or authorized Community Cloud session was available. Local no-key Chrome smoke tests passed uploads, QA/comparison downloads, malformed-input recovery, and disabled investigation. Those results do not verify a public deployment. The current manual procedure was checked against the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
