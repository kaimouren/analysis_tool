# Concurrency and resource exhaustion

Run `python benchmarks/adversarial.py`. This is an in-process analysis proxy, not a multi-browser Streamlit load test or a tenant-security certification. Each scenario runs in a fresh child process; RSS is sampled every 5 ms. Input construction is excluded; ingestion and profiling are timed. The machine uses Windows/Python 3.11.3, pandas 2.3.3, NumPy 2.4.6 and eight logical CPUs. Single observations are not latency percentiles and scheduling affects results.

## Actual shared-state failure and fix

The first 2/5/10-thread experiment produced matching deterministic profiles and no files, but **left process-global warnings filters changed**. Added filters included `All-NaN slice encountered` and `elementwise` warnings. Serializing only the explicit CSV/date `catch_warnings` blocks did not fix it: pandas/NumPy use additional warning contexts internally on Python 3.11.

V1.1 therefore serializes the public `load_csv` and `profile_dataframe` entry points through a shared reentrant lock. These operations queue within one Python process; they no longer offer parallel profiling throughput. The full rerun restores filters and matches sequential profiles. The lock protects these app entry points against each other, not arbitrary third-party threads, private helper callers, multiple processes or host memory exhaustion. It is intentionally a small local-tool fix, not distributed scheduling.

## Measured resource scenarios

| Scenario | Wall seconds | Sampled peak process RSS MiB | Outcome |
|---|---:|---:|---|
| too_wide | 0.0043 | 74.29 | rejected |
| huge_cell | 0.0086 | 74.96 | rejected |
| huge_strings | 0.39 | 147.0 | accepted |
| many_columns | 0.8638 | 79.88 | accepted |
| unique | 0.9577 | 126.15 | accepted |
| mixed | 2.8799 | 129.36 | accepted |
| duplicates | 1.0868 | 98.79 | accepted |
| strings | 1.4039 | 107.73 | accepted |

`too_wide` contains 201 columns and rejects; `huge_cell` contains a 300,000-character value and rejects safely. `huge_strings` contains 100 distinct cells of approximately 60,000 characters, within the new guard; `many_columns` is 100 rows by the supported 200 columns. Unique, pathological mixed and duplicate-heavy cases have 100,000 rows; the string-heavy case has 50,000 rows. No default row/column/file/cell budget was raised. Rejection results include safe reasons in the JSON artifact. No case crashed or wrote files to its empty temporary working directory.

## Simultaneous caller proxy

Each caller receives a distinct 10,000-row, four-column CSV (about 370 KB). A barrier releases 2, 5 or 10 threads together. Before timing, each input is profiled sequentially to establish an exact JSON fingerprint oracle. Every simultaneous result must match its own oracle and column name, preserve warning filters, and leave the temporary working directory empty. Provider calls are disabled/absent.

| Simultaneous callers | Batch wall seconds | Slowest caller seconds | Sampled peak RSS MiB | Increment above warm baseline MiB |
|---|---:|---:|---:|---:|
| 2 | 0.6374 | 0.6269 | 86.17 | 3.63 |
| 5 | 1.4846 | 1.4731 | 95.41 | 12.79 |
| 10 | 3.2652 | 3.2392 | 98.55 | 10.14 |

All profiles matched sequential results, each retained its own session-specific column, filters were restored, and no files were observed. Peak memory includes the process, input bytes, warm allocator and sequential-oracle setup. It does not represent a cold Streamlit server. It also excludes chart/browser transport, retained session frames/reports, uploads waiting in Streamlit and provider SDK traffic. There is no claim that ten hosted users at maximum limits are safe.

## API amplification and analytical limits

The experiment made zero provider calls. Analytically, if each of N visitors clicks once, up to N explanation requests can be in flight; repeated clicks/sessions have no quota bound. The per-call token/time limit does not limit aggregate spending. A shared server key exposes the administrator's budget. No paid load test was performed.

At the 256 MiB deep-frame guard, ten retained frames alone could approach 2.5 GiB, before decoded text, input buffers, charts or intermediates. That is a rough arithmetic exposure estimate, not measured maximum process memory. Serialized compute does not prevent many waiting sessions from retaining input or results.

## Before serious hosting

Define sensitivity/retention requirements; add authenticated admission, bounded pending work, per-user file/request quotas, host memory limits, cancellation/timeouts, provider spending controls and representative browser/session load tests. Use process isolation only if measured parallel-work requirements justify it. V1.1 adds none of that infrastructure and remains a bounded exploratory tool. Public deployment and remote CI remain unverified.

## Benchmark interpretation

`benchmarks/v1-1-results.json` records fresh-environment core-only profiling for 500, 10,000 and 100,000 rows. The resource table above includes ingestion and different data distributions, so it is not a direct speed comparison. Earlier development runs overlapped installation/tests and were slower; the retained acceptance measurements ran the suites sequentially. Even these single runs show timing variability. The V1 500,000-row experiment remains historical and explicitly outside supported UI limits.


## V1.2 lock-scope review

A temporary single-thread trace of `warnings.catch_warnings` around the real loader/profiler located contexts in pandas `pandas_dtype`, `maybe_cast_to_integer_array`, `asarray_tuplesafe`, `is_extension_array_dtype`, masked comparison operations, `where`, `nanmedian`, and quantile index construction, in addition to application CSV/date contexts. This confirms that local warning capture remains global state on Python 3.11 and the sensitive work is distributed throughout common operations.

A parser-only lock already failed in V1.1. Narrowing around every current private pandas/NumPy call would be version-fragile and miss contexts added by dependency updates; removing only the application's warning filters would not remove those internal contexts. The smallest defensible release change is therefore to retain the reentrant lock over public ingestion/profiling. No monkeypatch of the warnings machinery is shipped. The instrumentation ran temporarily in one diagnostic process and was restored immediately. This is a correctness-first choice, not a claim that serialization is universally optimal. A future supported runtime with context-local warnings could justify a separately measured change.

Concurrent callers queue for analysis; there is still no bounded admission or multi-user hosting guarantee. V1.2 reruns output/filter-restoration tests and the existing resource/concurrency harness, with results in VALIDATION.md.
