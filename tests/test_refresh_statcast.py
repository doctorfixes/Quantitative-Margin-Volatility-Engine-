"""Comprehensive tests for scripts.refresh_statcast."""

import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.refresh_statcast import (
    DEFAULT_OUTPUT_PATH,
    fetch_recent_statcast,
    main,
    save_data,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_statcast_df():
    """Minimal Statcast-like DataFrame for testing."""
    return pd.DataFrame(
        {
            "game_date": pd.date_range("2024-04-01", periods=5),
            "player_name": ["A", "B", "C", "D", "E"],
            "exit_velocity": [90.0, 95.0, 88.0, 101.0, 82.0],
            "launch_angle": [20.0, 25.0, 10.0, 28.0, -5.0],
        }
    )


@pytest.fixture()
def tmp_output(tmp_path):
    """A temp file path for saving CSV output."""
    return str(tmp_path / "test_output.csv")


# ---------------------------------------------------------------------------
# fetch_recent_statcast
# ---------------------------------------------------------------------------


class TestFetchRecentStatcast:
    def test_raises_import_error_when_pybaseball_missing(self):
        with patch.dict("sys.modules", {"pybaseball": None}):
            with pytest.raises(ImportError, match="pybaseball"):
                fetch_recent_statcast(days_back=7)

    def test_returns_dataframe(self, sample_statcast_df):
        mock_statcast = MagicMock(return_value=sample_statcast_df)
        mock_module = MagicMock()
        mock_module.statcast = mock_statcast
        with patch.dict("sys.modules", {"pybaseball": mock_module}):
            result = fetch_recent_statcast(days_back=7)
        assert isinstance(result, pd.DataFrame)

    def test_calls_statcast_with_date_strings(self, sample_statcast_df):
        end_date = datetime(2024, 4, 10)
        mock_statcast = MagicMock(return_value=sample_statcast_df)
        mock_module = MagicMock()
        mock_module.statcast = mock_statcast
        with patch.dict("sys.modules", {"pybaseball": mock_module}):
            fetch_recent_statcast(days_back=7, end_date=end_date)
        call_kwargs = mock_statcast.call_args
        assert call_kwargs.kwargs["start_dt"] == "2024-04-03"
        assert call_kwargs.kwargs["end_dt"] == "2024-04-10"

    def test_default_end_date_is_today(self, sample_statcast_df):
        today = datetime.today().strftime("%Y-%m-%d")
        mock_statcast = MagicMock(return_value=sample_statcast_df)
        mock_module = MagicMock()
        mock_module.statcast = mock_statcast
        with patch.dict("sys.modules", {"pybaseball": mock_module}):
            fetch_recent_statcast(days_back=1)
        assert mock_statcast.call_args.kwargs["end_dt"] == today

    def test_days_back_zero_raises_value_error(self, sample_statcast_df):
        with pytest.raises(ValueError, match="days_back"):
            fetch_recent_statcast(days_back=0)

    def test_negative_days_back_raises_value_error(self):
        with pytest.raises(ValueError, match="days_back"):
            fetch_recent_statcast(days_back=-5)

    def test_custom_days_back_computes_correct_start(self, sample_statcast_df):
        end_date = datetime(2024, 5, 1)
        mock_statcast = MagicMock(return_value=sample_statcast_df)
        mock_module = MagicMock()
        mock_module.statcast = mock_statcast
        with patch.dict("sys.modules", {"pybaseball": mock_module}):
            fetch_recent_statcast(days_back=30, end_date=end_date)
        assert mock_statcast.call_args.kwargs["start_dt"] == "2024-04-01"

    def test_returned_df_unchanged_from_mock(self, sample_statcast_df):
        mock_statcast = MagicMock(return_value=sample_statcast_df)
        mock_module = MagicMock()
        mock_module.statcast = mock_statcast
        with patch.dict("sys.modules", {"pybaseball": mock_module}):
            result = fetch_recent_statcast(days_back=7)
        assert len(result) == len(sample_statcast_df)


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------


class TestSaveData:
    def test_returns_path_string(self, sample_statcast_df, tmp_output):
        result = save_data(sample_statcast_df, output_path=tmp_output)
        assert isinstance(result, str)

    def test_file_created(self, sample_statcast_df, tmp_output):
        save_data(sample_statcast_df, output_path=tmp_output)
        assert os.path.isfile(tmp_output)

    def test_file_content_matches_dataframe(self, sample_statcast_df, tmp_output):
        save_data(sample_statcast_df, output_path=tmp_output)
        loaded = pd.read_csv(tmp_output)
        assert list(loaded.columns) == list(sample_statcast_df.columns)
        assert len(loaded) == len(sample_statcast_df)

    def test_returned_path_matches_argument(self, sample_statcast_df, tmp_output):
        returned = save_data(sample_statcast_df, output_path=tmp_output)
        assert returned == tmp_output

    def test_creates_parent_directory(self, sample_statcast_df, tmp_path):
        nested_path = str(tmp_path / "nested" / "dir" / "output.csv")
        save_data(sample_statcast_df, output_path=nested_path)
        assert os.path.isfile(nested_path)

    def test_defaults_to_default_output_path(self, sample_statcast_df):
        """save_data uses DEFAULT_OUTPUT_PATH when no path is given."""
        with patch("scripts.refresh_statcast.os.makedirs") as mock_makedirs, \
             patch.object(sample_statcast_df, "to_csv") as mock_to_csv:
            returned = save_data(sample_statcast_df)
        assert returned == DEFAULT_OUTPUT_PATH

    def test_empty_dataframe_saved(self, tmp_output):
        empty_df = pd.DataFrame(columns=["a", "b"])
        save_data(empty_df, output_path=tmp_output)
        loaded = pd.read_csv(tmp_output)
        assert loaded.empty

    def test_overwrites_existing_file(self, sample_statcast_df, tmp_output):
        save_data(sample_statcast_df, output_path=tmp_output)
        small_df = sample_statcast_df.head(2)
        save_data(small_df, output_path=tmp_output)
        loaded = pd.read_csv(tmp_output)
        assert len(loaded) == 2


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_returns_dataframe(self, sample_statcast_df, tmp_path):
        mock_module = MagicMock()
        mock_module.statcast = MagicMock(return_value=sample_statcast_df)
        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.dict("sys.modules", {"pybaseball": mock_module}), \
             patch("scripts.refresh_statcast.DEFAULT_OUTPUT_PATH", output_path):
            result = main()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_statcast_df)

    def test_main_creates_output_file(self, sample_statcast_df, tmp_path):
        mock_module = MagicMock()
        mock_module.statcast = MagicMock(return_value=sample_statcast_df)
        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.dict("sys.modules", {"pybaseball": mock_module}), \
             patch("scripts.refresh_statcast.DEFAULT_OUTPUT_PATH", output_path):
            main()
        assert os.path.isfile(output_path)

    def test_main_prints_record_count(self, sample_statcast_df, tmp_path, capsys):
        mock_module = MagicMock()
        mock_module.statcast = MagicMock(return_value=sample_statcast_df)
        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.dict("sys.modules", {"pybaseball": mock_module}), \
             patch("scripts.refresh_statcast.DEFAULT_OUTPUT_PATH", output_path):
            main()
        out = capsys.readouterr().out
        assert str(len(sample_statcast_df)) in out


# ---------------------------------------------------------------------------
# DEFAULT_OUTPUT_PATH sanity check
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_output_path_ends_with_csv(self):
        assert DEFAULT_OUTPUT_PATH.endswith(".csv")

    def test_default_output_path_contains_data_dir(self):
        assert "data" in DEFAULT_OUTPUT_PATH
