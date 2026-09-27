"""Rebuild the planted example with a fixed random seed."""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 480
frame = pd.DataFrame({
    "customer_id": [f"CUS-{i:05d}" for i in range(n)],
    "age": rng.integers(20, 66, n),
    "annual_income": rng.normal(65000, 14000, n).round(2),
    "engagement_score": rng.uniform(20, 80, n).round(3),
    "region": rng.choice(["North", "South", "East", "West"], n),
    "country": "US",
    "account_status": ["active"]*470 + ["paused"]*10,
    "tenure_months": rng.integers(1, 120, n).astype(str),
    "joined_date": pd.date_range("2022-01-01", periods=n).strftime("%Y-%m-%d"),
})
frame.loc[:139, "annual_income"] = np.nan
frame.loc[200:224, "annual_income"] = 950000
frame.loc[20:65, "region"] = None
frame.loc[10:49, "tenure_months"] = "unknown"
frame = pd.concat([frame, frame.iloc[300:320]], ignore_index=True)
frame.to_csv(Path(__file__).with_name("messy_sample.csv"), index=False)
print(f"Generated {len(frame)} rows")
