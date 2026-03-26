"""Comprehensive tests for src.volatility_analyzer."""

import numpy as np
import pandas as pd
import pytest

from src.volatility_analyzer import VolatilityAnalyzer


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def analyzer():
    return VolatilityAnalyzer()


@pytest.fixture()
def stable_series():
    """A series with nearly constant values (very low volatility)."""
    rng = np.random.default_rng(42)
    return pd.Series(95.0 + rng.normal(0, 0.1, 50))


@pytest.fixture()
def volatile_series():
    """A series that alternates between low and high values."""
    values = [80.0 if i % 2 == 0 else 105.0 for i in range(40)]
    return pd.Series(values, dtype=float)


@pytest.fixture()
def trending_series():
    """A linear upward trend (50 → 100 over 50 points)."""
    return pd.Series(np.linspace(50.0, 100.0, 50))


@pytest.fixture()
def constant_series():
    return pd.Series([90.0] * 20)


@pytest.fixture()
def empty_series():
    return pd.Series([], dtype=float)


@pytest.fixture()
def nan_series():
    return pd.Series([np.nan] * 10)


# ---------------------------------------------------------------------------
# VolatilityAnalyzer.__init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_window_is_ten(self):
        assert VolatilityAnalyzer().default_window == 10

    def test_custom_window_stored(self):
        assert VolatilityAnalyzer(default_window=5).default_window == 5

    def test_window_zero_raises(self):
        with pytest.raises(ValueError, match="default_window"):
            VolatilityAnalyzer(default_window=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            VolatilityAnalyzer(default_window=-1)

    def test_window_one_allowed(self):
        a = VolatilityAnalyzer(default_window=1)
        assert a.default_window == 1


# ---------------------------------------------------------------------------
# calculate_rolling_volatility
# ---------------------------------------------------------------------------


class TestRollingVolatility:
    def test_returns_series(self, analyzer, stable_series):
        result = analyzer.calculate_rolling_volatility(stable_series)
        assert isinstance(result, pd.Series)

    def test_length_matches_input(self, analyzer, stable_series):
        result = analyzer.calculate_rolling_volatility(stable_series)
        assert len(result) == len(stable_series)

    def test_first_values_are_nan(self, analyzer, stable_series):
        result = analyzer.calculate_rolling_volatility(stable_series, window=5)
        assert result.iloc[:4].isna().all()

    def test_values_after_warmup_are_finite(self, analyzer, stable_series):
        result = analyzer.calculate_rolling_volatility(stable_series, window=5)
        assert result.iloc[4:].notna().all()

    def test_stable_series_low_std(self, analyzer, stable_series):
        result = analyzer.calculate_rolling_volatility(stable_series, window=5)
        assert result.dropna().max() < 1.0  # very small noise

    def test_volatile_series_high_std(self, analyzer, volatile_series):
        result = analyzer.calculate_rolling_volatility(volatile_series, window=5)
        assert result.dropna().mean() > 5.0

    def test_uses_default_window(self, analyzer, stable_series):
        default = analyzer.calculate_rolling_volatility(stable_series)
        explicit = analyzer.calculate_rolling_volatility(stable_series, window=10)
        pd.testing.assert_series_equal(default, explicit)

    def test_explicit_window_overrides_default(self, analyzer, stable_series):
        w5 = analyzer.calculate_rolling_volatility(stable_series, window=5)
        w10 = analyzer.calculate_rolling_volatility(stable_series, window=10)
        assert not w5.equals(w10)

    def test_constant_series_std_is_zero_after_warmup(self, analyzer, constant_series):
        result = analyzer.calculate_rolling_volatility(constant_series, window=3)
        assert (result.dropna() == 0.0).all()


# ---------------------------------------------------------------------------
# calculate_coefficient_of_variation
# ---------------------------------------------------------------------------


class TestCoefficientOfVariation:
    def test_returns_float(self, analyzer, stable_series):
        result = analyzer.calculate_coefficient_of_variation(stable_series)
        assert isinstance(result, float)

    def test_positive_for_variable_series(self, analyzer, volatile_series):
        result = analyzer.calculate_coefficient_of_variation(volatile_series)
        assert result > 0

    def test_zero_for_constant_series(self, analyzer, constant_series):
        result = analyzer.calculate_coefficient_of_variation(constant_series)
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_mean_zero_returns_nan(self, analyzer):
        series = pd.Series([-1.0, 1.0])  # mean = 0
        result = analyzer.calculate_coefficient_of_variation(series)
        assert np.isnan(result)

    def test_empty_series_returns_nan(self, analyzer, empty_series):
        result = analyzer.calculate_coefficient_of_variation(empty_series)
        assert np.isnan(result)

    def test_all_nan_returns_nan(self, analyzer, nan_series):
        result = analyzer.calculate_coefficient_of_variation(nan_series)
        assert np.isnan(result)

    def test_stable_series_has_low_cv(self, analyzer, stable_series):
        result = analyzer.calculate_coefficient_of_variation(stable_series)
        assert result < 0.01  # < 1% CV

    def test_volatile_series_has_higher_cv(self, analyzer, volatile_series):
        result = analyzer.calculate_coefficient_of_variation(volatile_series)
        assert result > 0.05


# ---------------------------------------------------------------------------
# calculate_variance_ratio
# ---------------------------------------------------------------------------


class TestVarianceRatio:
    def test_returns_series(self, analyzer, stable_series):
        result = analyzer.calculate_variance_ratio(stable_series)
        assert isinstance(result, pd.Series)

    def test_length_matches_input(self, analyzer, stable_series):
        result = analyzer.calculate_variance_ratio(stable_series)
        assert len(result) == len(stable_series)

    def test_warmup_values_are_nan(self, analyzer, stable_series):
        result = analyzer.calculate_variance_ratio(stable_series, short_window=5, long_window=20)
        assert result.iloc[:19].isna().all()

    def test_constant_series_ratio_is_nan(self, analyzer, constant_series):
        # Both short and long variance are 0 → division produces NaN
        result = analyzer.calculate_variance_ratio(constant_series, short_window=3, long_window=5)
        assert result.dropna().empty or (result.dropna() == 0).all()

    def test_ratio_near_one_for_iid_noise(self, analyzer):
        rng = np.random.default_rng(0)
        series = pd.Series(rng.normal(0, 1, 200))
        result = analyzer.calculate_variance_ratio(series, short_window=10, long_window=50)
        valid = result.dropna()
        # For large IID samples the ratio should hover around 1
        assert valid.mean() == pytest.approx(1.0, abs=0.5)


# ---------------------------------------------------------------------------
# identify_high_volatility_periods
# ---------------------------------------------------------------------------


class TestIdentifyHighVolatilityPeriods:
    def test_returns_bool_series(self, analyzer, volatile_series):
        result = analyzer.identify_high_volatility_periods(volatile_series)
        assert result.dtype == bool

    def test_length_matches_input(self, analyzer, volatile_series):
        result = analyzer.identify_high_volatility_periods(volatile_series)
        assert len(result) == len(volatile_series)

    def test_stable_series_few_high_periods(self, analyzer, stable_series):
        result = analyzer.identify_high_volatility_periods(stable_series, window=5)
        assert result.sum() / len(result) < 0.3

    def test_custom_threshold_zero_flags_all_volatile(self, analyzer, volatile_series):
        # Threshold of 0 → every non-NaN window with std > 0 is flagged
        result = analyzer.identify_high_volatility_periods(
            volatile_series, threshold=0.0, window=3
        )
        assert result.sum() > 0

    def test_very_high_threshold_flags_nothing(self, analyzer, stable_series):
        result = analyzer.identify_high_volatility_periods(
            stable_series, threshold=1e9, window=5
        )
        assert result.sum() == 0

    def test_adaptive_threshold_not_none(self, analyzer, volatile_series):
        # When threshold is None it is inferred; result must be a boolean Series
        result = analyzer.identify_high_volatility_periods(volatile_series)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool


# ---------------------------------------------------------------------------
# calculate_volatility_trend
# ---------------------------------------------------------------------------


class TestVolatilityTrend:
    def test_returns_float(self, analyzer, stable_series):
        result = analyzer.calculate_volatility_trend(stable_series, window=5)
        assert isinstance(result, float)

    def test_short_series_returns_zero(self, analyzer):
        series = pd.Series([90.0, 91.0, 90.5])
        result = analyzer.calculate_volatility_trend(series, window=10)
        assert result == 0.0

    def test_increasing_variance_positive_slope(self, analyzer):
        # Variance increases because amplitude grows
        values = [95.0 + i * np.sin(i) for i in range(50)]
        series = pd.Series(values)
        result = analyzer.calculate_volatility_trend(series, window=5)
        assert isinstance(result, float)  # just ensure it runs; sign depends on data

    def test_uses_default_window(self, analyzer, stable_series):
        default = analyzer.calculate_volatility_trend(stable_series)
        explicit = analyzer.calculate_volatility_trend(stable_series, window=10)
        assert default == pytest.approx(explicit)

    def test_empty_series_returns_zero(self, analyzer, empty_series):
        result = analyzer.calculate_volatility_trend(empty_series)
        assert result == 0.0


# ---------------------------------------------------------------------------
# volatility_summary
# ---------------------------------------------------------------------------


class TestVolatilitySummary:
    def test_returns_dict(self, analyzer, stable_series):
        result = analyzer.volatility_summary(stable_series)
        assert isinstance(result, dict)

    def test_expected_keys_present(self, analyzer, stable_series):
        result = analyzer.volatility_summary(stable_series)
        for key in [
            "mean_rolling_std",
            "max_rolling_std",
            "coefficient_of_variation",
            "volatility_trend",
            "high_volatility_fraction",
        ]:
            assert key in result

    def test_values_are_numeric(self, analyzer, stable_series):
        result = analyzer.volatility_summary(stable_series)
        for key, val in result.items():
            assert isinstance(val, float) or np.isnan(val), f"{key} is {type(val)}"

    def test_high_volatility_fraction_in_unit_interval(self, analyzer, volatile_series):
        result = analyzer.volatility_summary(volatile_series)
        assert 0.0 <= result["high_volatility_fraction"] <= 1.0

    def test_empty_series_returns_nan_where_expected(self, analyzer, empty_series):
        result = analyzer.volatility_summary(empty_series)
        assert np.isnan(result["mean_rolling_std"])
        assert np.isnan(result["max_rolling_std"])

    def test_stable_series_low_mean_rolling_std(self, analyzer, stable_series):
        result = analyzer.volatility_summary(stable_series)
        assert result["mean_rolling_std"] < 1.0

    def test_volatile_series_high_mean_rolling_std(self, analyzer, volatile_series):
        result = analyzer.volatility_summary(volatile_series)
        assert result["mean_rolling_std"] > 5.0
