"""Detect performance stress points in Statcast time-series data."""

import numpy as np
import pandas as pd


class StressPointDetector:
    """Identify windows and patterns of elevated performance stress."""

    def __init__(self, default_window=10):
        if default_window < 1:
            raise ValueError("default_window must be >= 1")
        self.default_window = default_window

    # ------------------------------------------------------------------
    # Threshold-based detection
    # ------------------------------------------------------------------

    def detect_threshold_crossings(self, series, threshold):
        """Boolean Series that is True only at the *first* index of each
        contiguous below-threshold run (i.e. the crossing-downward point).

        All subsequent elements in the same run are False; the Series
        becomes True again only when the value crosses back above the
        threshold and then drops below it again.
        """
        below = series < threshold
        # diff of int representation: +1 = crossed downward, -1 = crossed upward
        crossings = below.astype(int).diff() == 1
        # Always mark the very first element if it starts below threshold
        if len(series) > 0:
            crossings.iloc[0] = below.iloc[0]
        return crossings

    def calculate_stress_score(self, series, low_threshold, high_threshold):
        """Element-wise stress indicator: 1 where *series* is outside
        [low_threshold, high_threshold], 0 otherwise."""
        outside = (series < low_threshold) | (series > high_threshold)
        return outside.astype(float)

    # ------------------------------------------------------------------
    # Run-length analysis
    # ------------------------------------------------------------------

    def find_consecutive_stress_runs(self, stress_series, min_run_length=3):
        """Return a list of dicts describing contiguous stress runs.

        Each dict has keys ``start`` (index label) and ``length`` (int).
        Only runs of at least *min_run_length* are included.
        """
        runs = []
        current_start = None
        current_length = 0

        for idx, val in stress_series.items():
            if val:
                if current_start is None:
                    current_start = idx
                    current_length = 1
                else:
                    current_length += 1
            else:
                if current_start is not None and current_length >= min_run_length:
                    runs.append({"start": current_start, "length": current_length})
                current_start = None
                current_length = 0

        # Flush any open run at the end of the series
        if current_start is not None and current_length >= min_run_length:
            runs.append({"start": current_start, "length": current_length})

        return runs

    # ------------------------------------------------------------------
    # Rolling stress score
    # ------------------------------------------------------------------

    def calculate_rolling_stress_score(
        self, series, window=None, percentile_low=10, percentile_high=90
    ):
        """Rolling mean of a binary stress indicator.

        The low/high thresholds are derived from *percentile_low* and
        *percentile_high* of the non-NaN values in *series*.
        Returns a Series of the same length with NaN in the warm-up window.
        """
        w = window if window is not None else self.default_window
        clean = series.dropna()
        if clean.empty:
            return pd.Series(np.nan, index=series.index)
        low = float(np.percentile(clean, percentile_low))
        high = float(np.percentile(clean, percentile_high))
        stress = self.calculate_stress_score(series, low, high)
        return stress.rolling(window=w).mean()

    # ------------------------------------------------------------------
    # Critical window identification
    # ------------------------------------------------------------------

    def identify_critical_windows(self, series, n_windows=5, window_size=None):
        """Return a sorted list of index labels for the *n_windows* most
        stressed rolling windows."""
        ws = window_size if window_size is not None else self.default_window
        rolling_stress = self.calculate_rolling_stress_score(series, window=ws)
        clean = rolling_stress.dropna()
        if clean.empty:
            return []
        n = min(n_windows, len(clean))
        return sorted(clean.nlargest(n).index.tolist())

    # ------------------------------------------------------------------
    # Composite stress summary
    # ------------------------------------------------------------------

    def stress_summary(self, series, window=None):
        """Return a dict with aggregate stress statistics for *series*."""
        ws = window if window is not None else self.default_window
        rolling = self.calculate_rolling_stress_score(series, window=ws)
        clean_vals = series.dropna()
        if clean_vals.empty:
            return {
                "mean_stress": np.nan,
                "max_stress": np.nan,
                "critical_window_count": 0,
            }
        low = float(np.percentile(clean_vals, 10))
        high = float(np.percentile(clean_vals, 90))
        stress = self.calculate_stress_score(series, low, high)
        runs = self.find_consecutive_stress_runs(stress.astype(bool), min_run_length=3)
        return {
            "mean_stress": float(stress.mean()),
            "max_stress": float(rolling.max()) if not rolling.dropna().empty else np.nan,
            "critical_window_count": len(runs),
        }
