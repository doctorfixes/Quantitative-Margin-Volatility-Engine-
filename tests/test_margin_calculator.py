"""Comprehensive tests for src.margin_calculator."""

import numpy as np
import pandas as pd
import pytest

from src.margin_calculator import (
    DEFAULT_EV_THRESHOLD,
    LEAGUE_AVG_WOBA,
    OPTIMAL_LA_MAX,
    OPTIMAL_LA_MIN,
    MarginCalculator,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def calc():
    return MarginCalculator()


@pytest.fixture()
def sample_df():
    """Ten batted-ball events across two players."""
    return pd.DataFrame(
        {
            "player_name": ["Alice"] * 5 + ["Bob"] * 5,
            "exit_velocity": [88.0, 95.0, 100.0, 97.0, 91.0, 80.0, 96.0, 103.0, 85.0, 99.0],
            "launch_angle": [12.0, 24.0, 30.0, 15.0, 5.0, 35.0, 22.0, 10.0, 28.0, 20.0],
            "estimated_woba_using_speedangle": [0.28, 0.42, 0.55, 0.39, 0.25, 0.20, 0.38, 0.60, 0.30, 0.45],
            "barrel": [0, 1, 1, 1, 0, 0, 1, 1, 0, 1],
        }
    )


@pytest.fixture()
def empty_df():
    return pd.DataFrame(
        columns=["player_name", "exit_velocity", "launch_angle",
                 "estimated_woba_using_speedangle", "barrel"]
    )


# ---------------------------------------------------------------------------
# MarginCalculator.__init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_ev_threshold(self):
        assert MarginCalculator().ev_threshold == DEFAULT_EV_THRESHOLD

    def test_custom_ev_threshold(self):
        calc = MarginCalculator(ev_threshold=90.0)
        assert calc.ev_threshold == 90.0


# ---------------------------------------------------------------------------
# calculate_hard_hit_rate
# ---------------------------------------------------------------------------


class TestHardHitRate:
    def test_all_above_threshold(self, calc):
        df = pd.DataFrame({"exit_velocity": [96.0, 97.0, 98.0]})
        assert calc.calculate_hard_hit_rate(df) == pytest.approx(1.0)

    def test_none_above_threshold(self, calc):
        df = pd.DataFrame({"exit_velocity": [80.0, 85.0, 90.0]})
        assert calc.calculate_hard_hit_rate(df) == pytest.approx(0.0)

    def test_half_above_threshold(self, calc):
        df = pd.DataFrame({"exit_velocity": [90.0, 95.0, 100.0, 80.0]})
        # 95 and 100 meet or exceed 95.0
        assert calc.calculate_hard_hit_rate(df) == pytest.approx(0.5)

    def test_exactly_at_threshold_counts(self, calc):
        df = pd.DataFrame({"exit_velocity": [95.0]})
        assert calc.calculate_hard_hit_rate(df) == pytest.approx(1.0)

    def test_empty_df_returns_zero(self, calc, empty_df):
        assert calc.calculate_hard_hit_rate(empty_df) == pytest.approx(0.0)

    def test_custom_threshold(self):
        calc_90 = MarginCalculator(ev_threshold=90.0)
        df = pd.DataFrame({"exit_velocity": [91.0, 89.0, 92.0]})
        assert calc_90.calculate_hard_hit_rate(df) == pytest.approx(2 / 3)

    def test_single_row_above(self, calc):
        df = pd.DataFrame({"exit_velocity": [100.0]})
        assert calc.calculate_hard_hit_rate(df) == pytest.approx(1.0)

    def test_single_row_below(self, calc):
        df = pd.DataFrame({"exit_velocity": [80.0]})
        assert calc.calculate_hard_hit_rate(df) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_exit_velocity_margin
# ---------------------------------------------------------------------------


class TestExitVelocityMargin:
    def test_positive_margin(self, calc):
        df = pd.DataFrame({"exit_velocity": [100.0, 105.0]})
        assert calc.calculate_exit_velocity_margin(df) == pytest.approx(7.5)

    def test_negative_margin(self, calc):
        df = pd.DataFrame({"exit_velocity": [85.0, 90.0]})
        assert calc.calculate_exit_velocity_margin(df) == pytest.approx(-7.5)

    def test_zero_margin(self, calc):
        df = pd.DataFrame({"exit_velocity": [95.0, 95.0]})
        assert calc.calculate_exit_velocity_margin(df) == pytest.approx(0.0)

    def test_empty_df_returns_zero(self, calc, empty_df):
        assert calc.calculate_exit_velocity_margin(empty_df) == pytest.approx(0.0)

    def test_single_row(self, calc):
        df = pd.DataFrame({"exit_velocity": [100.0]})
        assert calc.calculate_exit_velocity_margin(df) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# calculate_launch_angle_efficiency
# ---------------------------------------------------------------------------


class TestLaunchAngleEfficiency:
    def test_all_in_window(self, calc):
        df = pd.DataFrame({"launch_angle": [15.0, 20.0, 25.0, 30.0, 10.0]})
        assert calc.calculate_launch_angle_efficiency(df) == pytest.approx(1.0)

    def test_none_in_window(self, calc):
        df = pd.DataFrame({"launch_angle": [5.0, 35.0, -5.0, 40.0]})
        assert calc.calculate_launch_angle_efficiency(df) == pytest.approx(0.0)

    def test_boundary_values_included(self, calc):
        df = pd.DataFrame({"launch_angle": [OPTIMAL_LA_MIN, OPTIMAL_LA_MAX]})
        assert calc.calculate_launch_angle_efficiency(df) == pytest.approx(1.0)

    def test_half_in_window(self, calc):
        df = pd.DataFrame({"launch_angle": [20.0, 5.0]})
        assert calc.calculate_launch_angle_efficiency(df) == pytest.approx(0.5)

    def test_empty_df_returns_zero(self, calc, empty_df):
        assert calc.calculate_launch_angle_efficiency(empty_df) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_barrel_rate
# ---------------------------------------------------------------------------


class TestBarrelRate:
    def test_all_barrels(self, calc):
        df = pd.DataFrame({"barrel": [1, 1, 1]})
        assert calc.calculate_barrel_rate(df) == pytest.approx(1.0)

    def test_no_barrels(self, calc):
        df = pd.DataFrame({"barrel": [0, 0, 0]})
        assert calc.calculate_barrel_rate(df) == pytest.approx(0.0)

    def test_mixed_barrels(self, calc):
        df = pd.DataFrame({"barrel": [1, 0, 1, 0]})
        assert calc.calculate_barrel_rate(df) == pytest.approx(0.5)

    def test_missing_barrel_column_raises(self, calc):
        df = pd.DataFrame({"exit_velocity": [95.0]})
        with pytest.raises(KeyError, match="barrel"):
            calc.calculate_barrel_rate(df)

    def test_empty_df_returns_zero(self, calc):
        df = pd.DataFrame({"barrel": pd.Series([], dtype=float)})
        assert calc.calculate_barrel_rate(df) == pytest.approx(0.0)

    def test_single_barrel(self, calc):
        df = pd.DataFrame({"barrel": [1]})
        assert calc.calculate_barrel_rate(df) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_expected_woba_margin
# ---------------------------------------------------------------------------


class TestExpectedWobaMargin:
    def test_above_league_avg(self, calc):
        df = pd.DataFrame({"estimated_woba_using_speedangle": [0.400, 0.380]})
        expected = (0.400 + 0.380) / 2 - LEAGUE_AVG_WOBA
        assert calc.calculate_expected_woba_margin(df) == pytest.approx(expected)

    def test_below_league_avg(self, calc):
        df = pd.DataFrame({"estimated_woba_using_speedangle": [0.250, 0.270]})
        expected = (0.250 + 0.270) / 2 - LEAGUE_AVG_WOBA
        assert calc.calculate_expected_woba_margin(df) == pytest.approx(expected)

    def test_exactly_at_avg_returns_zero(self, calc):
        df = pd.DataFrame({"estimated_woba_using_speedangle": [LEAGUE_AVG_WOBA]})
        assert calc.calculate_expected_woba_margin(df) == pytest.approx(0.0)

    def test_missing_column_raises(self, calc):
        df = pd.DataFrame({"exit_velocity": [95.0]})
        with pytest.raises(KeyError, match="estimated_woba"):
            calc.calculate_expected_woba_margin(df)

    def test_empty_df_returns_zero(self, calc):
        df = pd.DataFrame({"estimated_woba_using_speedangle": pd.Series([], dtype=float)})
        assert calc.calculate_expected_woba_margin(df) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_composite_margin
# ---------------------------------------------------------------------------


class TestCompositeMargin:
    def test_returns_float(self, calc, sample_df):
        result = calc.calculate_composite_margin(sample_df)
        assert isinstance(result, float)

    def test_empty_df_returns_zero(self, calc, empty_df):
        assert calc.calculate_composite_margin(empty_df) == pytest.approx(0.0)

    def test_all_high_quality_positive(self, calc):
        df = pd.DataFrame(
            {
                "exit_velocity": [100.0] * 5,
                "launch_angle": [20.0] * 5,
            }
        )
        result = calc.calculate_composite_margin(df)
        # hhr=1, lae=1, ev_margin_norm=(5/10)=0.5 → mean ≈ 0.833
        assert result > 0

    def test_all_low_quality_negative_or_low(self, calc):
        df = pd.DataFrame(
            {
                "exit_velocity": [70.0] * 5,
                "launch_angle": [50.0] * 5,
            }
        )
        result = calc.calculate_composite_margin(df)
        # hhr=0, lae=0, ev_margin_norm=(−25/10)=−2.5 → mean < 0
        assert result < 0

    def test_single_row_above_threshold(self, calc):
        df = pd.DataFrame({"exit_velocity": [100.0], "launch_angle": [20.0]})
        result = calc.calculate_composite_margin(df)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# player_margin_summary
# ---------------------------------------------------------------------------


class TestPlayerMarginSummary:
    def test_returns_dataframe(self, calc, sample_df):
        result = calc.player_margin_summary(sample_df)
        assert isinstance(result, pd.DataFrame)

    def test_one_row_per_player(self, calc, sample_df):
        result = calc.player_margin_summary(sample_df)
        assert len(result) == sample_df["player_name"].nunique()

    def test_expected_columns_present(self, calc, sample_df):
        result = calc.player_margin_summary(sample_df)
        for col in ["player_name", "hard_hit_rate", "ev_margin", "la_efficiency", "composite_margin"]:
            assert col in result.columns

    def test_empty_df_returns_empty_summary(self, calc, empty_df):
        result = calc.player_margin_summary(empty_df)
        assert result.empty

    def test_single_player(self, calc):
        df = pd.DataFrame(
            {
                "player_name": ["Carlos"] * 3,
                "exit_velocity": [90.0, 96.0, 98.0],
                "launch_angle": [20.0, 25.0, 15.0],
            }
        )
        result = calc.player_margin_summary(df)
        assert len(result) == 1
        assert result.iloc[0]["player_name"] == "Carlos"

    def test_values_are_floats(self, calc, sample_df):
        result = calc.player_margin_summary(sample_df)
        for col in ["hard_hit_rate", "ev_margin", "la_efficiency", "composite_margin"]:
            assert result[col].dtype == float
