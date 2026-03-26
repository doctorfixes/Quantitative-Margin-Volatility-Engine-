"""Calculate efficiency margins for Statcast contact-quality metrics."""

import numpy as np
import pandas as pd

# Optimal launch-angle window (degrees) for elevated hard contact
OPTIMAL_LA_MIN = 10
OPTIMAL_LA_MAX = 30

# League-average wOBA used as the composite baseline
LEAGUE_AVG_WOBA = 0.320

# Hard-hit threshold (mph)
DEFAULT_EV_THRESHOLD = 95.0


class MarginCalculator:
    """Compute efficiency margin metrics from a Statcast DataFrame."""

    def __init__(self, ev_threshold=DEFAULT_EV_THRESHOLD):
        self.ev_threshold = ev_threshold

    # ------------------------------------------------------------------
    # Individual metrics
    # ------------------------------------------------------------------

    def calculate_hard_hit_rate(self, df):
        """Fraction of batted balls at or above *ev_threshold* mph."""
        if df.empty:
            return 0.0
        return float((df["exit_velocity"] >= self.ev_threshold).sum() / len(df))

    def calculate_exit_velocity_margin(self, df):
        """Mean exit velocity minus the hard-hit threshold."""
        if df.empty:
            return 0.0
        return float(df["exit_velocity"].mean() - self.ev_threshold)

    def calculate_launch_angle_efficiency(self, df):
        """Fraction of batted balls within the optimal launch-angle window."""
        if df.empty:
            return 0.0
        mask = (df["launch_angle"] >= OPTIMAL_LA_MIN) & (df["launch_angle"] <= OPTIMAL_LA_MAX)
        return float(mask.sum() / len(df))

    def calculate_barrel_rate(self, df):
        """Mean barrel flag value (fraction of barrels)."""
        if "barrel" not in df.columns:
            raise KeyError("Column 'barrel' not found in DataFrame")
        if df.empty:
            return 0.0
        return float(df["barrel"].mean())

    def calculate_expected_woba_margin(self, df):
        """Mean xwOBA minus the league-average baseline."""
        col = "estimated_woba_using_speedangle"
        if col not in df.columns:
            raise KeyError(f"Column '{col}' not found in DataFrame")
        if df.empty:
            return 0.0
        return float(df[col].mean() - LEAGUE_AVG_WOBA)

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------

    def calculate_composite_margin(self, df):
        """Weighted composite of hard-hit rate, LA efficiency, and EV margin.

        Each component is first normalised to a comparable scale then averaged.
        EV margin is divided by 10 to bring it into the 0–1 range.
        """
        if df.empty:
            return 0.0
        hhr = self.calculate_hard_hit_rate(df)
        lae = self.calculate_launch_angle_efficiency(df)
        ev_margin_norm = self.calculate_exit_velocity_margin(df) / 10.0
        return float((hhr + lae + ev_margin_norm) / 3.0)

    # ------------------------------------------------------------------
    # Per-player aggregation
    # ------------------------------------------------------------------

    def player_margin_summary(self, df):
        """Return a DataFrame with one row per player and all margin metrics."""
        if df.empty:
            return pd.DataFrame(
                columns=["player_name", "hard_hit_rate", "ev_margin",
                         "la_efficiency", "composite_margin"]
            )
        records = []
        for player, group in df.groupby("player_name"):
            records.append({
                "player_name": player,
                "hard_hit_rate": self.calculate_hard_hit_rate(group),
                "ev_margin": self.calculate_exit_velocity_margin(group),
                "la_efficiency": self.calculate_launch_angle_efficiency(group),
                "composite_margin": self.calculate_composite_margin(group),
            })
        return pd.DataFrame(records)
