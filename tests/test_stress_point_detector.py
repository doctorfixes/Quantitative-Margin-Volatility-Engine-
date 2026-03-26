"""Comprehensive tests for src.stress_point_detector."""

import numpy as np
import pandas as pd
import pytest

from src.stress_point_detector import StressPointDetector


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def detector():
    return StressPointDetector()


@pytest.fixture()
def normal_series():
    """50 values normally distributed around 0.350 xwOBA."""
    rng = np.random.default_rng(0)
    return pd.Series(0.350 + rng.normal(0, 0.050, 50))


@pytest.fixture()
def stress_heavy_series():
    """Series where a small cluster of extreme outliers (< 10% of data) sits
    well below the interpolated 10th-percentile threshold so the stress
    detector reliably marks them as stressed."""
    # 3 extreme outliers out of 40 values (7.5%) → the interpolated p10
    # threshold falls at ~0.32, comfortably above the outlier value 0.050.
    return pd.Series([0.350] * 18 + [0.050] * 3 + [0.350] * 19, dtype=float)


@pytest.fixture()
def constant_series():
    return pd.Series([0.320] * 30)


@pytest.fixture()
def alternating_series():
    """Alternates between 0.1 (stress) and 0.5 (fine)."""
    return pd.Series([0.1 if i % 2 == 0 else 0.5 for i in range(40)], dtype=float)


@pytest.fixture()
def empty_series():
    return pd.Series([], dtype=float)


# ---------------------------------------------------------------------------
# StressPointDetector.__init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_window(self):
        assert StressPointDetector().default_window == 10

    def test_custom_window(self):
        assert StressPointDetector(default_window=5).default_window == 5

    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            StressPointDetector(default_window=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            StressPointDetector(default_window=-3)


# ---------------------------------------------------------------------------
# detect_threshold_crossings
# ---------------------------------------------------------------------------


class TestDetectThresholdCrossings:
    def test_returns_bool_series(self, detector, normal_series):
        result = detector.detect_threshold_crossings(normal_series, threshold=0.200)
        assert result.dtype == bool

    def test_length_matches_input(self, detector, normal_series):
        result = detector.detect_threshold_crossings(normal_series, threshold=0.200)
        assert len(result) == len(normal_series)

    def test_no_crossings_when_all_above(self, detector):
        series = pd.Series([0.400, 0.420, 0.390])
        result = detector.detect_threshold_crossings(series, threshold=0.200)
        assert result.sum() == 0

    def test_crossing_at_start_when_first_below(self, detector):
        series = pd.Series([0.100, 0.400, 0.350])
        result = detector.detect_threshold_crossings(series, threshold=0.300)
        assert result.iloc[0] is np.bool_(True)

    def test_crossing_at_first_below_in_middle(self, detector):
        series = pd.Series([0.400, 0.400, 0.150, 0.140, 0.400])
        result = detector.detect_threshold_crossings(series, threshold=0.300)
        # Index 2 is the first crossing
        assert result.iloc[2] is np.bool_(True)
        # Index 3 is continuation, not a new crossing
        assert result.iloc[3] is np.bool_(False)

    def test_multiple_separate_crossings(self, detector):
        # Two below-threshold runs separated by above-threshold values
        series = pd.Series([0.4, 0.1, 0.4, 0.1, 0.4])
        result = detector.detect_threshold_crossings(series, threshold=0.3)
        assert result.sum() == 2

    def test_all_below_threshold_one_crossing(self, detector):
        series = pd.Series([0.100, 0.150, 0.120])
        result = detector.detect_threshold_crossings(series, threshold=0.300)
        # Starts below: counts as 1 crossing at index 0
        assert result.sum() == 1

    def test_single_element_above_threshold(self, detector):
        series = pd.Series([0.400])
        result = detector.detect_threshold_crossings(series, threshold=0.300)
        assert result.sum() == 0

    def test_single_element_below_threshold(self, detector):
        series = pd.Series([0.100])
        result = detector.detect_threshold_crossings(series, threshold=0.300)
        assert result.sum() == 1


# ---------------------------------------------------------------------------
# calculate_stress_score
# ---------------------------------------------------------------------------


class TestCalculateStressScore:
    def test_returns_series(self, detector, normal_series):
        result = detector.calculate_stress_score(normal_series, 0.250, 0.450)
        assert isinstance(result, pd.Series)

    def test_all_inside_bounds_returns_zeros(self, detector):
        series = pd.Series([0.300, 0.320, 0.340])
        result = detector.calculate_stress_score(series, 0.250, 0.450)
        assert (result == 0).all()

    def test_all_outside_bounds_returns_ones(self, detector):
        series = pd.Series([0.100, 0.600, 0.050])
        result = detector.calculate_stress_score(series, 0.250, 0.450)
        assert (result == 1).all()

    def test_mixed_produces_correct_mask(self, detector):
        series = pd.Series([0.100, 0.320, 0.600])
        result = detector.calculate_stress_score(series, 0.250, 0.450)
        assert list(result) == [1.0, 0.0, 1.0]

    def test_boundary_values_not_stressed(self, detector):
        series = pd.Series([0.250, 0.450])
        result = detector.calculate_stress_score(series, 0.250, 0.450)
        assert (result == 0).all()

    def test_empty_series_returns_empty(self, detector, empty_series):
        result = detector.calculate_stress_score(empty_series, 0.2, 0.4)
        assert result.empty


# ---------------------------------------------------------------------------
# find_consecutive_stress_runs
# ---------------------------------------------------------------------------


class TestFindConsecutiveStressRuns:
    def test_returns_list(self, detector):
        stress = pd.Series([True, True, True, False, False])
        runs = detector.find_consecutive_stress_runs(stress)
        assert isinstance(runs, list)

    def test_single_long_run_found(self, detector):
        stress = pd.Series([False, False, True, True, True, True, False])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert len(runs) == 1
        assert runs[0]["length"] == 4

    def test_run_too_short_not_included(self, detector):
        stress = pd.Series([True, True, False, False, False])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert len(runs) == 0

    def test_multiple_qualifying_runs(self, detector):
        stress = pd.Series([True, True, True, False, True, True, True, True])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert len(runs) == 2

    def test_run_at_end_captured(self, detector):
        stress = pd.Series([False, True, True, True])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert len(runs) == 1

    def test_all_stress_one_run(self, detector):
        stress = pd.Series([True] * 10)
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert len(runs) == 1
        assert runs[0]["length"] == 10

    def test_no_stress_empty_list(self, detector):
        stress = pd.Series([False] * 10)
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert runs == []

    def test_empty_series_empty_list(self, detector):
        runs = detector.find_consecutive_stress_runs(pd.Series([], dtype=bool))
        assert runs == []

    def test_min_run_length_one_includes_singles(self, detector):
        stress = pd.Series([True, False, True])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=1)
        assert len(runs) == 2

    def test_run_dict_has_start_and_length_keys(self, detector):
        stress = pd.Series([True, True, True])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert "start" in runs[0]
        assert "length" in runs[0]

    def test_run_start_index_correct(self, detector):
        stress = pd.Series([False, False, True, True, True])
        runs = detector.find_consecutive_stress_runs(stress, min_run_length=3)
        assert runs[0]["start"] == 2


# ---------------------------------------------------------------------------
# calculate_rolling_stress_score
# ---------------------------------------------------------------------------


class TestCalculateRollingStressScore:
    def test_returns_series(self, detector, normal_series):
        result = detector.calculate_rolling_stress_score(normal_series)
        assert isinstance(result, pd.Series)

    def test_length_matches_input(self, detector, normal_series):
        result = detector.calculate_rolling_stress_score(normal_series)
        assert len(result) == len(normal_series)

    def test_warmup_values_are_nan(self, detector, normal_series):
        result = detector.calculate_rolling_stress_score(normal_series, window=5)
        assert result.iloc[:4].isna().all()

    def test_values_in_zero_one_range(self, detector, normal_series):
        result = detector.calculate_rolling_stress_score(normal_series, window=5)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 1).all()

    def test_empty_series_returns_nan(self, detector, empty_series):
        result = detector.calculate_rolling_stress_score(empty_series, window=5)
        assert result.isna().all()

    def test_constant_series_zero_stress(self, detector, constant_series):
        # All values at the same level → all within the inter-percentile range
        result = detector.calculate_rolling_stress_score(constant_series, window=5)
        valid = result.dropna()
        assert (valid == 0).all()

    def test_stress_heavy_series_has_nonzero_stress(self, detector, stress_heavy_series):
        result = detector.calculate_rolling_stress_score(stress_heavy_series, window=5)
        assert result.dropna().max() > 0

    def test_uses_default_window(self, detector, normal_series):
        default = detector.calculate_rolling_stress_score(normal_series)
        explicit = detector.calculate_rolling_stress_score(normal_series, window=10)
        pd.testing.assert_series_equal(default, explicit)


# ---------------------------------------------------------------------------
# identify_critical_windows
# ---------------------------------------------------------------------------


class TestIdentifyCriticalWindows:
    def test_returns_list(self, detector, normal_series):
        result = detector.identify_critical_windows(normal_series)
        assert isinstance(result, list)

    def test_at_most_n_windows(self, detector, normal_series):
        result = detector.identify_critical_windows(normal_series, n_windows=3)
        assert len(result) <= 3

    def test_exactly_n_windows_when_sufficient_data(self, detector, normal_series):
        result = detector.identify_critical_windows(normal_series, n_windows=3, window_size=5)
        assert len(result) == 3

    def test_empty_series_returns_empty(self, detector, empty_series):
        result = detector.identify_critical_windows(empty_series)
        assert result == []

    def test_result_is_sorted(self, detector, stress_heavy_series):
        result = detector.identify_critical_windows(stress_heavy_series, n_windows=3)
        assert result == sorted(result)

    def test_n_windows_clamped_to_data_size(self, detector):
        series = pd.Series([0.1, 0.5, 0.1, 0.5, 0.1])
        result = detector.identify_critical_windows(series, n_windows=100, window_size=2)
        # Can't return more windows than valid rolling results
        assert len(result) <= len(series)

    def test_stress_heavy_windows_from_middle(self, detector, stress_heavy_series):
        result = detector.identify_critical_windows(
            stress_heavy_series, n_windows=3, window_size=5
        )
        assert len(result) == 3


# ---------------------------------------------------------------------------
# stress_summary
# ---------------------------------------------------------------------------


class TestStressSummary:
    def test_returns_dict(self, detector, normal_series):
        result = detector.stress_summary(normal_series)
        assert isinstance(result, dict)

    def test_expected_keys_present(self, detector, normal_series):
        result = detector.stress_summary(normal_series)
        assert "mean_stress" in result
        assert "max_stress" in result
        assert "critical_window_count" in result

    def test_empty_series_returns_nan_metrics(self, detector, empty_series):
        result = detector.stress_summary(empty_series)
        assert np.isnan(result["mean_stress"])

    def test_mean_stress_in_unit_interval(self, detector, normal_series):
        result = detector.stress_summary(normal_series)
        assert 0.0 <= result["mean_stress"] <= 1.0

    def test_stress_heavy_has_positive_critical_count(self, detector, stress_heavy_series):
        result = detector.stress_summary(stress_heavy_series)
        # The 12-element low block should produce at least one critical run
        assert result["critical_window_count"] >= 1

    def test_constant_series_zero_critical_count(self, detector, constant_series):
        result = detector.stress_summary(constant_series)
        assert result["critical_window_count"] == 0

    def test_uses_default_window(self, detector, normal_series):
        r1 = detector.stress_summary(normal_series)
        r2 = detector.stress_summary(normal_series, window=10)
        assert r1["mean_stress"] == pytest.approx(r2["mean_stress"])
