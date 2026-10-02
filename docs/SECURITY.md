# Security and privacy

## V2.1 investigation additions

Investigation requires explicit UI consent before sending the question, real
column names/types, chosen periods/filters and bounded group aggregates to the
configured model. Group labels, numeric extrema and small-group statistics can
be sensitive. This differs from anonymized V1/V2 explanation payloads. There is
no raw-row tool; parser samples and DataFrame attributes are excluded. No
investigation is automatically persisted to the comparison history.

Only allowlisted tools with strict non-executable arguments are callable. No
filesystem, shell, secret-reading, external connector or DataFrame mutation
capability exists in the planner context. Questions, schema and labels are
untrusted data; copied contexts prevent mutation of authoritative evidence.
Unknown tools, repeated calls and invalid columns fail with bounded structured
errors. Final prose is not accepted from the model: selected code-authored claims
must cite existing evidence. Primary/contradictory results cannot be omitted.
The UI renders answer text without interpreting dataset labels as HTML/Markdown.

The model can still choose a valid but irrelevant analysis. Limits bound steps,
attempts, errors and accepted context/result size; the elapsed deadline is soft,
not worker preemption. No per-user cost quota, hard response-byte cap, differential
privacy or new multi-tenant isolation is provided. Trace/export retains observable
actions and aggregates, never hidden reasoning. Review downloads before sharing.
See [contracts and limits](INVESTIGATION.md) and [red-team evidence](V2_1_RED_TEAM.md).

## V2 comparison additions

Both uploads remain in server memory. Comparison results can contain bounded local category examples; the provider payload and Markdown export exclude them. Provider payloads also exclude names, timestamps and extrema. Generated text remains unverified prose with schema/lexical guardrails.

`QA_HISTORY_PATH` explicitly enables local SQLite metadata persistence and is intended for trusted single-user installations only. A Save action stores basename filenames, time, counts, summary and finding-type counts; no rows, categories, column names or generated prose. The latest 50 runs remain. Filenames may be sensitive. Corrupt-file backups remain until manually removed. This history has no per-user isolation: leave the variable unset on public demos. Source-control ignore rules exclude history files. Cloud-local files may be ephemeral.

## Threat assumptions

CSV uploads, filenames, headers, and provider prose are untrusted content. The server administrator, installed dependencies and explicitly approved provider endpoints are trusted. V1 is a bounded, single-process exploration tool; it is not an authenticated multi-tenant service or hardened sandbox. Use synthetic data for public demos. No authentication was added.

## Data handling

In local mode, the browser uploads to the local Python server. In hosted mode, the entire CSV leaves the browser for the hosting server even when AI is disabled. DataFrames, profiles, bounded parser examples, and generated reports live in Streamlit session memory. The application does not write uploads or provider credentials to disk. Framework memory retention, OS swap, crash dumps, browser downloads, and host telemetry are outside this guarantee; there is no secure-erasure promise.

Uploaded filenames are labels, never server paths. We parse comma-delimited text with pandas, never execute it, and never unpickle or deserialize uploaded Python objects. Binary control bytes and UTF-16-style input are rejected with UTF-8 export guidance. UTF-8 and Latin-1 are supported; Latin-1 fallback cannot establish original encoding. Duplicate/blank headers are rejected before pandas can rename them. Short rows are still null-padded by pandas. Default NA tokens can collapse distinct source representations; leading-zero numeric codes can lose formatting during inference.

Limits: 10 MiB encoded input, 200,000 rows, 200 columns, 2,000,000 cells, 256 MiB deep DataFrame memory. The row reader requests at most one beyond the permitted rows to detect overflow, then rejects the input rather than silently sampling. Decoding, parsing and intermediate objects allocate memory before the final frame-size check. These are guardrails, not a process memory ceiling. Concurrent sessions can exceed host resources.

## Optional external API

Clicking Generate AI explanations sends dataset dimensions, aggregate missing/duplicate rates, score and penalty breakdown, and the top five findings' rule fields to the configured provider. Actual column names are replaced by aliases. Raw rows, frequency values, local parser examples and other evidence are excluded by an explicit field allowlist. Aggregates themselves can be sensitive. Provider retention and network policies depend on the chosen provider and account; this repository makes no retention guarantee.

Credentials are resolved from explicit input, environment or Streamlit secrets. Server keys never populate widgets. Browser-selected endpoints must exactly match the default OpenAI endpoint, the administrator-configured endpoint, or `QA_ALLOWED_LLM_BASE_URLS` (comma-separated, environment-only). URL credentials, query strings and fragments are rejected. A different endpoint also requires the visitor's own key. Administrators can deliberately approve local HTTP endpoints; prefer HTTPS for remote use. This is an endpoint-selection control, not a DNS/redirect/network sandbox. Only trust approved providers and enforce egress policy at the host if needed. Direct Python callers control their own endpoints.

Provider calls have a 25-second timeout and no SDK retries. Schema, expected issue order, extra-field and numeric-claim checks reject malformed explanations. Generated prose is rendered as plain text in the UI; reports escape Markdown data fields. Uploaded values never become instructions in the prompt. These controls reduce prompt injection and accidental numerical claims but do not prove prose true: spelled-out false claims remain possible.

## Exports and diagnostics

The export is Markdown, not CSV or a spreadsheet; spreadsheet formula injection is not an executable export path. Column names and findings remain in reports, so review them before sharing. No automatic report publication exists. Application logs contain only allowlisted event names, counts, durations, encoding labels and categorical failure reasons. No filenames, raw cells, headers, keys, endpoint URLs or exception text are emitted by this logger. Framework/provider libraries have their own logging behavior; do not enable verbose request logging on sensitive deployments.

Original analysis errors are chained for local debugging; users see safe actionable messages. Provider errors are reduced to safe categories. Avoid copying raw exception traces into public issues because parser/provider exceptions can contain content.

## Known limitations and deployment responsibility

No rate limiting, identity, quotas, encrypted storage, tenant isolation guarantee, dependency vulnerability audit or penetration test is included. A configured server key allows visitors to incur provider costs. Public demos should omit server credentials and use non-sensitive fixtures. TLS, access control, egress restrictions, resource quotas, retention and secret rotation belong to the host deployment. `.env.example` contains placeholders; `.env` and `.streamlit/secrets.toml` are ignored. The application does not load `.env` automatically.

Report vulnerabilities privately to your deployment/repository owner. Do not attach credentials or customer CSVs to public issues.


## V1.1 adversarial changes

CSV fields now have a 65,536-character bound checked before pandas; direct DataFrames receive the same text guard. Finite native numeric magnitudes over 1e150 are rejected to prevent overflowed statistical summaries. Large parsed integer extrema retain their integer representation, while aggregate statistics are explicitly approximate. Whole public ingestion/profiling calls share a reentrant lock because pandas/NumPy warning contexts also mutate process-global filters on Python 3.11. This protects application analysis calls from one another, not unrelated third-party threads or process-level resource exhaustion.

Provider output is revalidated even if presented as an existing mutated Pydantic instance. A 2,000-token request cap and narrow identifier/certainty/destructive-advice rejection rules reduce clear violations. Paraphrased invented facts still pass; read LLM_FAILURE_MODES.md. No rate limit, response-byte cap, identity or semantic truth detector was added.


## V1.2 representation evidence

Ingestion retains bounded pre-pandas field snippets: at most three per column, 80 characters each, selected only within the first 100 logical records (up to 48,000 retained characters at the default column limit, plus metadata). Temporary candidate lists are also bounded. Samples can contain sensitive data and are visible in the local/server session UI; they are never sent in the aggregate-only provider payload, application logs or Markdown export. Existing parsed preview/example privacy boundaries still apply. The app does not retain a second full token table or promise raw-byte fidelity.
