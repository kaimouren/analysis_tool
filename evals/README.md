# Detector evaluation

Run `python evals/run.py --output evals/results.json` from the repository root after installing development requirements. `datasets.py` constructs eight fixed synthetic datasets: clean, missingness, duplicate, outlier, mixed-type, messy-string, combined and header-only edge case. Construction is the dataset source; no private files are required. Each frame passes through actual CSV ingestion before analysis.

Expected `(issue_type, column, severity)` tuples and hand-computed scores live alongside construction. They are not captured from detector output. The runner exits nonzero for any missing/unexpected finding or score mismatch. An unexpected severity counts as an extra tuple and a missed expected tuple. The checked-in result is one actual run; runtimes vary.

The suite has 11 expected findings, all detected in the recorded run, with zero extras or misses. A clean dataset's zero findings and expected score are also asserted. The planted 500-row regression remains in pytest. These are regression fixtures, not a representative accuracy study; zero fixture false positives does not establish a population false-positive rate. AI explanation quality is not evaluated by this suite.
