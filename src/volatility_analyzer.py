"""Analyze volatility in Statcast time-series metrics."""

import numpy as np
import pandas as pd


class VolatilityAnalyzer:
    """Compute rolling and aggregate volatility statistics on a numeric Series."""

    def __init__(self, default_window=10):
        if default_window < 1:
            raise ValueError("default_window must be >= 1")
        self.default_window = default_window

    # ------------------------------------------------------------------
    # Core volatility metrics
    # ------------------------------------------------------------------

    def calculate_rolling_volatility(self, series, window=None):
        """Rolling standard deviation of *series*.

        Returns a Series of the same length; the first ``window - 1`` values
        are NaN (standard pandas behaviour).
        """
        w = window if window is not None else self.default_window
        return series.rolling(window=w).std()

    def calculate_coefficient_of_variation(self, series):
        """Population coefficient of variation (std / |mean|).

        Returns ``np.nan`` when the mean is zero or the series is empty.
        """
        clean = series.dropna()
        if clean.empty:
            return np.nan
        mean = clean.mean()
        if mean == 0:
            return np.nan
        return float(clean.std() / abs(mean))

    def calculate_variance_ratio(self, series, short_window=5, long_window=20):
        """Ratio of short-window variance to long-window variance.

        Returns a Series aligned with *series*.  Zeros in the long-window
        variance are replaced with NaN to avoid division by zero.
        """
        short_var = series.rolling(window=short_window).var()
        long_var = series.rolling(window=long_window).var().replace(0, np.nan)
        return short_var / long_var

    # ------------------------------------------------------------------
    # High-volatility detection
    # ------------------------------------------------------------------

    def identify_high_volatility_periods(self, series, threshold=None, window=None):
        """Boolean Series that is True where rolling std exceeds *threshold*.

        When *threshold* is None it defaults to ``mean + 1 std`` of the
        rolling-volatility series (adaptive threshold).
        """
        w = window if window is not None else self.default_window
        rolling_std = self.calculate_rolling_volatility(series, w)
        if threshold is None:
            threshold = rolling_std.mean() + rolling_std.std()
        return rolling_std > threshold

    def calculate_volatility_trend(self, series, window=None):
        """Slope of the rolling-volatility series (linear regression).

        A positive slope means volatility is increasing over time.
        Returns 0.0 when there are fewer than two non-NaN observations.
        """
        w = window if window is not None else self.default_window
        rolling_std = self.calculate_rolling_volatility(series, w).dropna()
        if len(rolling_std) < 2:
            return 0.0
        x = np.arange(len(rolling_std))
        slope = float(np.polyfit(x, rolling_std.values, 1)[0])
        return slope

    # ------------------------------------------------------------------
    # Aggregate summary
    # ------------------------------------------------------------------

    def volatility_summary(self, series, window=None):
        """Return a dict with key volatility statistics for *series*."""
        w = window if window is not None else self.default_window
        rolling_std = self.calculate_rolling_volatility(series, w)
        high_vol = self.identify_high_volatility_periods(series, window=w)
        return {
            "mean_rolling_std": float(rolling_std.mean()) if not rolling_std.dropna().empty else np.nan,
            "max_rolling_std": float(rolling_std.max()) if not rolling_std.dropna().empty else np.nan,
            "coefficient_of_variation": self.calculate_coefficient_of_variation(series),
            "volatility_trend": self.calculate_volatility_trend(series, w),
            "high_volatility_fraction": float(high_vol.sum() / len(series)) if len(series) > 0 else 0.0,
        }
