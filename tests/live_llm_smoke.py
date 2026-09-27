"""Manually make one small provider call using environment configuration."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from llm import UNAVAILABLE, explain_profile
from qa_core import profile_dataframe


def main() -> int:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("SKIPPED: no API key configured; live LLM behavior remains unverified.")
        return 0
    profile = profile_dataframe(pd.DataFrame({"sample": ["a", "a", "b"]}))
    _, status = explain_profile(profile, model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    print("PASS: live structured explanation received." if status != UNAVAILABLE
          else "UNVERIFIED: provider call failed or returned rejected output; deterministic fallback worked.")
    return 0 if status != UNAVAILABLE else 1


if __name__ == "__main__":
    raise SystemExit(main())
