"""
Tests for scripts/refresh_statcast.py

External dependencies (pybaseball.statcast, pandas I/O) are mocked so the
tests run offline without hitting any network or filesystem.
"""
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd

import scripts.refresh_statcast as rs


# ---------------------------------------------------------------------------
# fetch_latest_statcast
# ---------------------------------------------------------------------------

class TestFetchLatestStatcast:
    def test_calls_statcast_with_yesterday(self):
        """statcast() is called with yesterday's date for both start and end."""
        yesterday = date.today() - timedelta(days=1)
        expected_date = yesterday.strftime("%Y-%m-%d")
        mock_df = pd.DataFrame({"col": [1, 2]})

        with patch("scripts.refresh_statcast.statcast", return_value=mock_df) as mock_sc:
            rs.fetch_latest_statcast()
            mock_sc.assert_called_once_with(start_dt=expected_date, end_dt=expected_date)

    def test_returns_dataframe_from_statcast(self):
        """The DataFrame returned by statcast() is passed through unchanged."""
        mock_df = pd.DataFrame({"pitch_type": ["FF", "SL"], "release_speed": [95.1, 87.3]})

        with patch("scripts.refresh_statcast.statcast", return_value=mock_df):
            result = rs.fetch_latest_statcast()
            pd.testing.assert_frame_equal(result, mock_df)

    def test_returns_none_when_statcast_returns_none(self):
        """If statcast() returns None the function propagates it."""
        with patch("scripts.refresh_statcast.statcast", return_value=None):
            result = rs.fetch_latest_statcast()
            assert result is None

    def test_returns_empty_dataframe_when_statcast_returns_empty(self):
        """An empty DataFrame from statcast() is returned as-is."""
        with patch("scripts.refresh_statcast.statcast", return_value=pd.DataFrame()):
            result = rs.fetch_latest_statcast()
            assert isinstance(result, pd.DataFrame)
            assert result.empty


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_saves_csv_when_data_returned(self, tmp_path):
        """main() writes the DataFrame to OUTPUT_PATH when data is available."""
        mock_df = pd.DataFrame({"a": [1, 2, 3]})
        output_file = tmp_path / "latest_statcast.csv"

        with patch("scripts.refresh_statcast.fetch_latest_statcast", return_value=mock_df), \
             patch("scripts.refresh_statcast.OUTPUT_PATH", str(output_file)), \
             patch("os.makedirs"):
            rs.main()

        assert output_file.exists()
        saved = pd.read_csv(str(output_file))
        assert list(saved.columns) == ["a"]
        assert len(saved) == 3

    def test_main_writes_empty_csv_when_data_is_none(self, tmp_path):
        """main() writes an empty CSV file when statcast returns None."""
        output_file = tmp_path / "latest_statcast.csv"

        with patch("scripts.refresh_statcast.fetch_latest_statcast", return_value=None), \
             patch("scripts.refresh_statcast.OUTPUT_PATH", str(output_file)), \
             patch("os.makedirs"):
            rs.main()

        assert output_file.exists()
        # pd.DataFrame().to_csv(index=False) writes a single empty line;
        # confirm the file is present but contains no data rows.
        content = output_file.read_text().strip()
        assert content == ""

    def test_main_writes_empty_csv_when_data_is_empty(self, tmp_path):
        """main() writes an empty CSV file when statcast returns an empty DataFrame."""
        output_file = tmp_path / "latest_statcast.csv"

        with patch("scripts.refresh_statcast.fetch_latest_statcast", return_value=pd.DataFrame()), \
             patch("scripts.refresh_statcast.OUTPUT_PATH", str(output_file)), \
             patch("os.makedirs"):
            rs.main()

        assert output_file.exists()
        content = output_file.read_text().strip()
        assert content == ""

    def test_main_creates_output_directory(self, tmp_path):
        """main() calls makedirs so the data/ directory is created if missing."""
        mock_df = pd.DataFrame({"x": [9]})
        output_file = tmp_path / "sub" / "latest_statcast.csv"

        with patch("scripts.refresh_statcast.fetch_latest_statcast", return_value=mock_df), \
             patch("scripts.refresh_statcast.OUTPUT_PATH", str(output_file)):
            rs.main()

        assert output_file.exists()
