"""Load, validate, and preprocess Statcast time-series data."""

import pandas as pd

REQUIRED_COLUMNS = [
    "game_date",
    "player_name",
    "exit_velocity",
    "launch_angle",
    "estimated_ba_using_speedangle",
    "estimated_woba_using_speedangle",
    "barrel",
]


class DataLoader:
    """Loads Statcast CSV data and prepares it for downstream analysis."""

    def __init__(self, data_path=None):
        self.data_path = data_path

    def load_from_csv(self, path=None):
        """Read a CSV file and return a DataFrame with game_date parsed."""
        csv_path = path if path is not None else self.data_path
        if csv_path is None:
            raise ValueError("No path provided. Pass a path or set data_path at construction.")
        df = pd.read_csv(csv_path, parse_dates=["game_date"])
        return df

    def validate_columns(self, df, required_columns=None):
        """Raise ValueError when *required_columns* are absent from *df*."""
        if required_columns is None:
            required_columns = REQUIRED_COLUMNS
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return True

    def preprocess(self, df):
        """Return a cleaned copy of *df*:
        - ``game_date`` is coerced to datetime
        - rows with NaN in ``exit_velocity`` or ``launch_angle`` are dropped
        """
        df = df.copy()
        if "game_date" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date"])
        numeric_cols = [c for c in ("exit_velocity", "launch_angle") if c in df.columns]
        if numeric_cols:
            df = df.dropna(subset=numeric_cols)
        df = df.reset_index(drop=True)
        return df
