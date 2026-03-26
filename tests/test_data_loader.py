"""Comprehensive tests for src.data_loader."""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from src.data_loader import DataLoader, REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def full_df():
    """A DataFrame that satisfies all REQUIRED_COLUMNS with clean data."""
    return pd.DataFrame(
        {
            "game_date": pd.date_range("2024-04-01", periods=10, freq="D"),
            "player_name": ["Alice"] * 5 + ["Bob"] * 5,
            "exit_velocity": [88.0, 92.0, 95.0, 101.0, 87.0, 93.0, 99.0, 78.0, 100.0, 85.0],
            "launch_angle": [15.0, 22.0, 30.0, 25.0, 10.0, 18.0, 28.0, 5.0, 20.0, 12.0],
            "estimated_ba_using_speedangle": [0.25, 0.32, 0.18, 0.40, 0.22, 0.28, 0.38, 0.10, 0.39, 0.21],
            "estimated_woba_using_speedangle": [0.30, 0.38, 0.22, 0.48, 0.27, 0.34, 0.46, 0.14, 0.47, 0.26],
            "barrel": [0, 0, 0, 1, 0, 0, 1, 0, 1, 0],
        }
    )


@pytest.fixture()
def df_with_nans(full_df):
    """Introduce NaN into exit_velocity row 2 and launch_angle row 4."""
    df = full_df.copy()
    df.loc[2, "exit_velocity"] = np.nan
    df.loc[4, "launch_angle"] = np.nan
    return df


@pytest.fixture()
def tmp_csv(full_df):
    """Write *full_df* to a temporary CSV and yield the path; clean up afterwards."""
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as fh:
        full_df.to_csv(fh.name, index=False)
        path = fh.name
    yield path
    os.unlink(path)


# ---------------------------------------------------------------------------
# DataLoader.__init__
# ---------------------------------------------------------------------------


class TestDataLoaderInit:
    def test_default_data_path_is_none(self):
        loader = DataLoader()
        assert loader.data_path is None

    def test_custom_data_path_stored(self):
        loader = DataLoader(data_path="/foo/bar.csv")
        assert loader.data_path == "/foo/bar.csv"


# ---------------------------------------------------------------------------
# DataLoader.load_from_csv
# ---------------------------------------------------------------------------


class TestLoadFromCsv:
    def test_returns_dataframe(self, tmp_csv):
        df = DataLoader().load_from_csv(tmp_csv)
        assert isinstance(df, pd.DataFrame)

    def test_row_count_preserved(self, full_df, tmp_csv):
        df = DataLoader().load_from_csv(tmp_csv)
        assert len(df) == len(full_df)

    def test_column_names_preserved(self, full_df, tmp_csv):
        df = DataLoader().load_from_csv(tmp_csv)
        assert set(full_df.columns) == set(df.columns)

    def test_game_date_parsed_as_datetime(self, tmp_csv):
        df = DataLoader().load_from_csv(tmp_csv)
        assert pd.api.types.is_datetime64_any_dtype(df["game_date"])

    def test_uses_instance_data_path_when_no_arg(self, tmp_csv):
        loader = DataLoader(data_path=tmp_csv)
        df = loader.load_from_csv()
        assert len(df) > 0

    def test_explicit_path_overrides_instance_path(self, full_df, tmp_csv):
        loader = DataLoader(data_path="/nonexistent.csv")
        df = loader.load_from_csv(path=tmp_csv)
        assert len(df) == len(full_df)

    def test_no_path_raises_value_error(self):
        with pytest.raises(ValueError, match="No path provided"):
            DataLoader().load_from_csv()

    def test_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            DataLoader().load_from_csv("/does/not/exist.csv")


# ---------------------------------------------------------------------------
# DataLoader.validate_columns
# ---------------------------------------------------------------------------


class TestValidateColumns:
    def test_valid_df_returns_true(self, full_df):
        assert DataLoader().validate_columns(full_df) is True

    def test_default_required_columns_used_when_none(self, full_df):
        # Explicitly check against the module-level constant
        assert DataLoader().validate_columns(full_df, REQUIRED_COLUMNS) is True

    def test_custom_columns_all_present(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        assert DataLoader().validate_columns(df, ["a", "b"]) is True

    def test_missing_single_column_raises_value_error(self):
        df = pd.DataFrame({"exit_velocity": [90.0]})
        with pytest.raises(ValueError, match="Missing required columns"):
            DataLoader().validate_columns(df, ["exit_velocity", "launch_angle"])

    def test_missing_multiple_columns_message_contains_all(self):
        df = pd.DataFrame({"only_col": [1]})
        with pytest.raises(ValueError) as exc_info:
            DataLoader().validate_columns(df, ["a", "b", "c"])
        msg = str(exc_info.value)
        assert "a" in msg
        assert "b" in msg
        assert "c" in msg

    def test_empty_required_list_always_passes(self, full_df):
        assert DataLoader().validate_columns(full_df, []) is True

    def test_empty_df_missing_columns_raises(self):
        df = pd.DataFrame()
        with pytest.raises(ValueError):
            DataLoader().validate_columns(df, ["exit_velocity"])


# ---------------------------------------------------------------------------
# DataLoader.preprocess
# ---------------------------------------------------------------------------


class TestPreprocess:
    def test_returns_new_dataframe(self, full_df):
        loader = DataLoader()
        result = loader.preprocess(full_df)
        assert result is not full_df

    def test_original_unchanged(self, df_with_nans):
        original_len = len(df_with_nans)
        DataLoader().preprocess(df_with_nans)
        assert len(df_with_nans) == original_len

    def test_nan_rows_in_exit_velocity_dropped(self, df_with_nans):
        result = DataLoader().preprocess(df_with_nans)
        assert result["exit_velocity"].isna().sum() == 0

    def test_nan_rows_in_launch_angle_dropped(self, df_with_nans):
        result = DataLoader().preprocess(df_with_nans)
        assert result["launch_angle"].isna().sum() == 0

    def test_two_nan_rows_removed(self, df_with_nans):
        # full_df has 10 rows; 2 NaN rows inserted
        result = DataLoader().preprocess(df_with_nans)
        assert len(result) == 8

    def test_index_reset_after_drop(self, df_with_nans):
        result = DataLoader().preprocess(df_with_nans)
        assert list(result.index) == list(range(len(result)))

    def test_game_date_string_coerced_to_datetime(self, full_df):
        df = full_df.copy()
        df["game_date"] = df["game_date"].astype(str)
        result = DataLoader().preprocess(df)
        assert pd.api.types.is_datetime64_any_dtype(result["game_date"])

    def test_already_datetime_not_broken(self, full_df):
        result = DataLoader().preprocess(full_df)
        assert pd.api.types.is_datetime64_any_dtype(result["game_date"])

    def test_empty_df_returns_empty(self):
        df = pd.DataFrame(columns=["game_date", "exit_velocity", "launch_angle"])
        result = DataLoader().preprocess(df)
        assert result.empty

    def test_all_nan_exit_velocity_produces_empty_df(self, full_df):
        df = full_df.copy()
        df["exit_velocity"] = np.nan
        result = DataLoader().preprocess(df)
        assert result.empty

    def test_no_game_date_column_does_not_raise(self):
        df = pd.DataFrame({"exit_velocity": [90.0, 91.0], "launch_angle": [15.0, 20.0]})
        result = DataLoader().preprocess(df)
        assert len(result) == 2

    def test_only_exit_velocity_nan_handled(self, full_df):
        df = full_df.copy()
        df.loc[0, "exit_velocity"] = np.nan
        result = DataLoader().preprocess(df)
        assert len(result) == 9


# ---------------------------------------------------------------------------
# Integration: load → validate → preprocess
# ---------------------------------------------------------------------------


class TestDataLoaderIntegration:
    def test_full_pipeline_produces_clean_df(self, full_df, tmp_csv):
        loader = DataLoader(data_path=tmp_csv)
        df = loader.load_from_csv()
        loader.validate_columns(df, REQUIRED_COLUMNS)
        clean = loader.preprocess(df)
        assert not clean.empty
        assert clean["exit_velocity"].isna().sum() == 0
        assert clean["launch_angle"].isna().sum() == 0
