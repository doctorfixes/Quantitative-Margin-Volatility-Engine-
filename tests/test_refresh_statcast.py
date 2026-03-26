"""
Tests for scripts/refresh_statcast.py

Coverage areas:
- fetch_latest_statcast: date calculation, correct arguments passed to statcast()
- main: non-empty DataFrame saved correctly
- main: empty DataFrame writes empty CSV without raising
- main: None return writes empty CSV without raising
- main: output directory is created if it does not exist
- OUTPUT_PATH: points inside the repository data/ directory
"""

import os
import sys
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Path setup — make `scripts` importable without installing the package
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import refresh_statcast as rsc  # noqa: E402  (import after path manipulation)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_df():
    """Return a small but realistic-looking Statcast DataFrame."""
    return pd.DataFrame(
        {
            "pitch_type": ["FF", "SL"],
            "release_speed": [95.2, 87.4],
            "batter": [123456, 654321],
            "game_date": ["2024-04-01", "2024-04-01"],
        }
    )


# ---------------------------------------------------------------------------
# Module-level constant tests
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Verify that module-level constants are correct."""

    def test_repo_root_is_parent_of_scripts(self):
        """REPO_ROOT should be the directory that contains the scripts/ folder."""
        assert os.path.isdir(os.path.join(rsc.REPO_ROOT, "scripts"))

    def test_output_path_inside_data_directory(self):
        """OUTPUT_PATH must be inside the data/ sub-directory of the repo root."""
        expected_dir = os.path.join(rsc.REPO_ROOT, "data")
        assert os.path.dirname(rsc.OUTPUT_PATH) == expected_dir

    def test_output_filename_is_csv(self):
        """The output file must have a .csv extension."""
        assert rsc.OUTPUT_PATH.endswith(".csv")

    def test_output_filename(self):
        """The output file should be named latest_statcast.csv."""
        assert os.path.basename(rsc.OUTPUT_PATH) == "latest_statcast.csv"


# ---------------------------------------------------------------------------
# fetch_latest_statcast tests
# ---------------------------------------------------------------------------


class TestFetchLatestStatcast:
    """Tests for the fetch_latest_statcast() function."""

    def test_fetches_yesterday(self):
        """fetch_latest_statcast must request data for *yesterday*."""
        mock_df = _sample_df()
        with patch("refresh_statcast.statcast", return_value=mock_df) as mock_statcast:
            rsc.fetch_latest_statcast()

        yesterday = date.today() - timedelta(days=1)
        expected_date_str = yesterday.strftime("%Y-%m-%d")

        mock_statcast.assert_called_once_with(
            start_dt=expected_date_str,
            end_dt=expected_date_str,
        )

    def test_returns_dataframe(self):
        """fetch_latest_statcast must return whatever statcast() returns."""
        mock_df = _sample_df()
        with patch("refresh_statcast.statcast", return_value=mock_df):
            returned = rsc.fetch_latest_statcast()

        assert returned is mock_df

    def test_start_and_end_dt_are_identical(self):
        """start_dt and end_dt must be the same (single-day fetch)."""
        with patch("refresh_statcast.statcast", return_value=pd.DataFrame()) as mock_statcast:
            rsc.fetch_latest_statcast()

        _, kwargs = mock_statcast.call_args
        assert kwargs["start_dt"] == kwargs["end_dt"]

    def test_date_format_is_iso(self):
        """The date string must follow YYYY-MM-DD format."""
        with patch("refresh_statcast.statcast", return_value=pd.DataFrame()) as mock_statcast:
            rsc.fetch_latest_statcast()

        _, kwargs = mock_statcast.call_args
        date_str = kwargs["start_dt"]
        # This will raise ValueError if the format doesn't match
        parsed = date.fromisoformat(date_str)
        assert parsed == date.today() - timedelta(days=1)

    def test_passes_through_none_from_statcast(self):
        """If statcast() returns None, fetch_latest_statcast must also return None."""
        with patch("refresh_statcast.statcast", return_value=None):
            result = rsc.fetch_latest_statcast()
        assert result is None

    def test_passes_through_empty_dataframe(self):
        """If statcast() returns an empty DataFrame, that must be propagated."""
        empty_df = pd.DataFrame()
        with patch("refresh_statcast.statcast", return_value=empty_df):
            result = rsc.fetch_latest_statcast()
        assert result is not None
        assert result.empty


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() orchestration function."""

    def test_saves_csv_when_data_returned(self, tmp_path):
        """main() must write a CSV file when statcast returns data."""
        mock_df = _sample_df()
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=mock_df),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        assert output_file.exists()
        saved = pd.read_csv(str(output_file))
        assert len(saved) == len(mock_df)
        assert list(saved.columns) == list(mock_df.columns)

    def test_csv_content_matches_dataframe(self, tmp_path):
        """The CSV written by main() must contain the exact same data."""
        mock_df = _sample_df()
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=mock_df),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        saved = pd.read_csv(str(output_file))
        pd.testing.assert_frame_equal(saved, mock_df)

    def test_writes_empty_csv_when_df_is_empty(self, tmp_path):
        """main() must write an empty CSV (not raise) when the DataFrame is empty."""
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=pd.DataFrame()),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        assert output_file.exists()
        # Empty CSV produced by pd.DataFrame().to_csv(index=False) has no rows
        content = output_file.read_text()
        assert content.strip() == ""

    def test_writes_empty_csv_when_none_returned(self, tmp_path):
        """main() must write an empty CSV (not raise) when statcast returns None."""
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=None),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        assert output_file.exists()
        content = output_file.read_text()
        assert content.strip() == ""

    def test_creates_output_directory_if_missing(self, tmp_path):
        """main() must create the output directory if it does not exist."""
        nested_output = tmp_path / "nested" / "dir" / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=_sample_df()),
            patch("refresh_statcast.OUTPUT_PATH", str(nested_output)),
        ):
            rsc.main()

        assert nested_output.exists()

    def test_does_not_raise_on_empty_data(self, tmp_path):
        """main() must not raise any exception when data is empty."""
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=pd.DataFrame()),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            try:
                rsc.main()
            except Exception as exc:
                pytest.fail(f"main() raised unexpectedly on empty data: {exc}")

    def test_does_not_raise_on_none_data(self, tmp_path):
        """main() must not raise any exception when None is returned."""
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=None),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            try:
                rsc.main()
            except Exception as exc:
                pytest.fail(f"main() raised unexpectedly with None data: {exc}")

    def test_row_count_printed_for_non_empty_data(self, tmp_path, capsys):
        """main() should print the number of rows saved when data is available."""
        mock_df = _sample_df()
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=mock_df),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        captured = capsys.readouterr()
        assert str(len(mock_df)) in captured.out

    def test_no_data_message_printed_for_empty_df(self, tmp_path, capsys):
        """main() should print a 'no data' message when the DataFrame is empty."""
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=pd.DataFrame()),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        captured = capsys.readouterr()
        assert "no statcast data" in captured.out.lower()

    def test_no_data_message_printed_for_none(self, tmp_path, capsys):
        """main() should print a 'no data' message when None is returned."""
        output_file = tmp_path / "latest_statcast.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=None),
            patch("refresh_statcast.OUTPUT_PATH", str(output_file)),
        ):
            rsc.main()

        captured = capsys.readouterr()
        assert "no statcast data" in captured.out.lower()

    def test_output_path_used_correctly(self, tmp_path):
        """The file must be written to exactly the path specified by OUTPUT_PATH."""
        expected_path = tmp_path / "custom_output.csv"

        with (
            patch("refresh_statcast.fetch_latest_statcast", return_value=_sample_df()),
            patch("refresh_statcast.OUTPUT_PATH", str(expected_path)),
        ):
            rsc.main()

        assert expected_path.exists()
        # Ensure no stray CSV was created elsewhere
        other_csvs = list(tmp_path.rglob("*.csv"))
        assert other_csvs == [expected_path]
