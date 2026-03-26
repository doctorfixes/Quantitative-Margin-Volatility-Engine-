"""Daily Statcast data refresh script.

Fetches recent pitch-level Statcast data via *pybaseball* and persists it
to ``data/latest_statcast.csv`` relative to the repository root.

Usage
-----
    python scripts/refresh_statcast.py

The script is invoked automatically by the ``axiom_statcast_refresh`` GitHub
Actions workflow on a daily schedule.
"""

import os
from datetime import datetime, timedelta

import pandas as pd

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_PATH = os.path.join(_REPO_ROOT, "data", "latest_statcast.csv")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_recent_statcast(days_back=7, end_date=None):
    """Return a DataFrame of Statcast records for the last *days_back* days.

    Parameters
    ----------
    days_back:
        How many calendar days back from *end_date* to query.
    end_date:
        Upper bound of the query window.  Defaults to today's date.

    Raises
    ------
    ImportError
        When *pybaseball* is not installed.
    ValueError
        When *days_back* is not a positive integer.
    """
    if days_back < 1:
        raise ValueError("days_back must be >= 1")

    try:
        from pybaseball import statcast  # noqa: PLC0415 – deferred optional import
    except ImportError as exc:
        raise ImportError(
            "pybaseball is required to fetch live data.  "
            "Install it with:  pip install pybaseball"
        ) from exc

    if end_date is None:
        end_date = datetime.today()
    start_date = end_date - timedelta(days=days_back)

    df = statcast(
        start_dt=start_date.strftime("%Y-%m-%d"),
        end_dt=end_date.strftime("%Y-%m-%d"),
    )
    return df


def save_data(df, output_path=None):
    """Persist *df* to *output_path* as CSV and return the path used.

    The parent directory is created automatically when it does not exist.
    """
    path = output_path if output_path is not None else DEFAULT_OUTPUT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def main():
    """Entry point: fetch and save recent Statcast data."""
    print("Fetching recent Statcast data…")
    df = fetch_recent_statcast(days_back=7)
    path = save_data(df)
    print(f"Saved {len(df):,} records to {path}")
    return df


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
