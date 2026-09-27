"""Record observable CSV normalization on fictional tokens without network access."""
import csv
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ingestion import load_csv
from qa_core import scalar

CASES = {
    "leading_zeros": ["00123", "00456"], "scientific": ["1e3", "2.5e-2"],
    "large_int64": ["9007199254740993", "9007199254740995"],
    "beyond_uint64": ["18446744073709551616", "18446744073709551617"],
    "missing_tokens": ["NA", "null", "ordinary"], "boolean_text": ["TRUE", "FALSE"],
    "locale": ["1.234,56", "1,234.56", "1,5", "1.5"],
    "date_like": ["01/02/2024", "2099-12-31", "2024-02-30"],
    "quoted_comma_and_newline": ["hello, world", "first\nsecond"],
    "unicode": ["東京", "café", "🙂", "Straße"],
}


def run():
    results = []
    for name, tokens in CASES.items():
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["value"])
        writer.writerows([[token] for token in tokens])
        data = stream.getvalue().encode("utf-8")
        frame, encoding = load_csv(data)
        results.append({"case": name, "source_tokens": tokens, "parsed_values": [scalar(v) for v in frame.value],
                        "dtype": str(frame.value.dtype), "encoding": encoding})
    frame, encoding = load_csv(b"\xef\xbb\xbfvalue\n00123\n")
    results.append({"case": "BOM", "columns": list(frame.columns), "parsed_values": [scalar(v) for v in frame.value], "encoding": encoding})
    return results


if __name__ == "__main__":
    results = run()
    (Path(__file__).parent / "inference-results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(f"Recorded {len(results)} CSV representation probes.")
