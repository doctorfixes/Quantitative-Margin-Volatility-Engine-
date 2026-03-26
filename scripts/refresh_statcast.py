"""
refresh_statcast.py

Fetches the most recent day's Statcast data using pybaseball and writes
it to data/latest_statcast.csv relative to the repository root.
"""

import os
from datetime import date, timedelta

import pandas as pd
from pybaseball import statcast

# Output path is always relative to the repository root so the workflow
# `git add data/latest_statcast.csv` step can find the file.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(REPO_ROOT, "data", "latest_statcast.csv")


def fetch_latest_statcast() -> pd.DataFrame:
    """Return Statcast data for yesterday (the most recent full game day)."""
    yesterday = date.today() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    print(f"Fetching Statcast data for {date_str} …")
    df = statcast(start_dt=date_str, end_dt=date_str)
    return df


def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df = fetch_latest_statcast()
    if df is None or df.empty:
        print("No Statcast data returned for the requested date.")
        # Write an empty file so the commit step does not fail on a missing path.
        pd.DataFrame().to_csv(OUTPUT_PATH, index=False)
    else:
        df.to_csv(OUTPUT_PATH, index=False)
        print(f"Saved {len(df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
