# V1.2.0 release note

Data QA Agent V1.2 makes uncertainty visible without changing default score policy 1.0. The summary now displays Quality Score and Critical/High/Medium/Low issue counts separately, with severe findings prominent regardless of score. Generated text is labeled "Generated interpretation. Verify before acting." Rejected provider output retains deterministic cards and authored guidance.

Suspicious and mixed columns can show up to three decoded pre-inference tokens, truncated to 80 characters, drawn from the first 100 logical records. These examples explain representation risk; they are not lossless source data, do not affect findings, and are excluded from LLM requests, logs and Markdown exports. Profile schema advances to 1.4; application version is 1.2.0.

Whole-analysis serialization remains after tracing warning contexts throughout pandas/NumPy operations. It protects process-global warning filters on the supported runtime, trading parallel throughput for predictable behavior. Per-input upload/memory guards remain unchanged; no hosted-capacity guarantee is added.

The README, deployment procedure and release evidence now distinguish deterministic evidence, heuristic rules and optional generated interpretation. See VALIDATION.md for actual platform, browser, concurrency and provider results. Remote GitHub Actions and public Streamlit deployment are not claimed without an observed successful run and tested public URL.

No data contracts, schema DSL, automatic cleaning, model training, target selection, authentication, database, background jobs, distributed engine or semantic LLM verifier was added.
