# CSV inference attack

Run `python evals/inference.py`. These observations are from the installed pandas version, not a universal promise across CSV libraries. The raw bytes are decoded, header/field limits checked, then pandas infers types and default missing tokens before QA sees a DataFrame. Parsing is not automatic cleaning, but it is not raw-file fidelity either.

| Probe | Raw source tokens | Parsed values | Inferred dtype |
|---|---|---|---|
| leading_zeros | ["00123", "00456"] | [123, 456] | int64 |
| scientific | ["1e3", "2.5e-2"] | [1000.0, 0.025] | float64 |
| large_int64 | ["9007199254740993", "9007199254740995"] | [9007199254740993, 9007199254740995] | int64 |
| beyond_uint64 | ["18446744073709551616", "18446744073709551617"] | ["18446744073709551616", "18446744073709551617"] | object |
| missing_tokens | ["NA", "null", "ordinary"] | [null, null, "ordinary"] | object |
| boolean_text | ["TRUE", "FALSE"] | [true, false] | bool |
| locale | ["1.234,56", "1,234.56", "1,5", "1.5"] | ["1.234,56", "1,234.56", "1,5", "1.5"] | object |
| date_like | ["01/02/2024", "2099-12-31", "2024-02-30"] | ["01/02/2024", "2099-12-31", "2024-02-30"] | object |
| quoted_comma_and_newline | ["hello, world", "first\nsecond"] | ["hello, world", "first\nsecond"] | object |
| unicode | ["東京", "café", "🙂", "Straße"] | ["東京", "café", "🙂", "Straße"] | object |
| BOM | "UTF-8 BOM + 00123" | [123] | int64 |

Quoted numeric IDs still become numbers; quoting is CSV syntax, not a request for string dtype. Leading zeros, exponent notation and distinctions among NA/null/empty tokens cannot be recovered from this inferred frame. Boolean-looking strings become booleans. Integers beyond uint64 remain strings in this probe; their semantic numeric parsing may still be approximate. Locale commas/parentheses remain text and can trigger mixed-parser warnings instead of conversion. Date-looking strings remain text at ingestion; the separate date heuristic tests parseability with month-first defaults. Embedded newlines and quoted commas remain within their cells. UTF-8 Unicode content survives; a BOM is removed and decoding reports UTF-8.

## Numeric hardening

V1 converted all finite numeric values to float64 before deriving extrema. Parsed integer 9007199254740993 therefore displayed an incorrect minimum of 9007199254740992. V1.1 takes extrema from the original parsed numeric series and flags large-integer arithmetic as approximate. Unique/duplicate counts use parsed values; means, quantiles and IQR workspace still use float64. Signed-int64 minimum is explicitly covered without overflowing an absolute-value calculation. This does not recover precision already lost by CSV inference in a mixed float column.

Finite native numerical magnitude above 1e150 is now rejected with rescaling guidance instead of emitting overflowed summaries (the baseline 1e308 probe produced infinite mean/std). This conservative supported-range bound leaves room for squaring in variance calculations; it is not a business validity rule. Infinities retain their existing explicit finding. Large numeric strings can remain text, which does not establish numerical fidelity.

## Limits and product language

The UI/report now says analysis uses parsed values and may normalize leading zeros and missing tokens. No cleaning is applied, but the former blanket statement that values are never modified was too broad. A future explicit schema/NA contract is the best route to preserving intentional representations; no new parsing-options product was added in V1.1. Latin-1 fallback still cannot identify the original encoding. Short rows are null-padded and blank physical lines may be skipped by pandas.


## V1.2 bounded pre-inference examples

The existing CSV preflight pass now samples decoded field values before pandas inference, limited to the first 100 logical records, three distinct retained examples per column and 80 characters per example. Recognized leading-zero, large-integer, NA-like, currency/percentage and ambiguous date tokens are prioritized within that window. A small fallback set provides context for columns later identified as mixed. Only lexical-risk or mixed columns expose examples in the profile/explorer. Collection uses bounded lists, not an additional full-file token table.

These are decoded CSV fields: quote syntax and BOM have already been interpreted, strings can be truncated, records are not mapped to parsed row numbers, and late anomalies may be absent. Samples support explanation only; scores and issue records are unchanged. Copies in profiles do not alias the frame's sample lists. Notebook DataFrames without ingestion metadata have no raw examples. Examples remain in server-session memory and are explicitly excluded from reports, LLM payloads and diagnostics. Tests cover leading zeros, large integers, NA-like tokens, currency, percentages, ambiguous dates and all three bounds.
