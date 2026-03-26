"""
Tests for scripts/refresh_statcast.py

External dependencies (pandas, pybaseball) are mocked so that these tests
run with only the standard library and pytest installed.
"""

import importlib
import os
import sys
import types
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers to build lightweight stubs for pandas and pybaseball
# ---------------------------------------------------------------------------

def _make_pandas_stub():
    """Return a minimal stub for pandas used by refresh_statcast."""
    pd = types.ModuleType("pandas")

    class DataFrame:
        def __init__(self, data=None):
            self._data = data or {}
            self.empty = not bool(data)

        def __len__(self):
            return len(self._data) if isinstance(self._data, list) else 0

        def to_csv(self, path, index=False):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write("")

    pd.DataFrame = DataFrame
    return pd


def _make_pybaseball_stub(return_value=None):
    """Return a minimal stub for pybaseball."""
    pybaseball = types.ModuleType("pybaseball")
    pybaseball.statcast = MagicMock(return_value=return_value)
    return pybaseball


def _import_module(pandas_stub, pybaseball_stub):
    """Import (or re-import) refresh_statcast with the given stubs injected."""
    module_name = "refresh_statcast"

    # Determine the scripts directory where refresh_statcast.py lives.
    scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    )

    # Save prior module and path state so we can restore it after import.
    old_refresh_module = sys.modules.get(module_name)
    old_pandas = sys.modules.get("pandas")
    old_pybaseball = sys.modules.get("pybaseball")
    path_was_modified = False

    try:
        # Remove cached version so we get a fresh import each time.
        sys.modules.pop(module_name, None)
        sys.modules["pandas"] = pandas_stub
        sys.modules["pybaseball"] = pybaseball_stub

        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
            path_was_modified = True

        module = importlib.import_module(module_name)
        return module
    finally:
        # Restore pandas module.
        if old_pandas is not None:
            sys.modules["pandas"] = old_pandas
        else:
            sys.modules.pop("pandas", None)

        # Restore pybaseball module.
        if old_pybaseball is not None:
            sys.modules["pybaseball"] = old_pybaseball
        else:
            sys.modules.pop("pybaseball", None)

        # Restore prior refresh_statcast module, if any.
        if old_refresh_module is not None:
            sys.modules[module_name] = old_refresh_module
        else:
            sys.modules.pop(module_name, None)

        # Undo sys.path modification performed for this import.
        if path_was_modified:
            try:
                sys.path.remove(scripts_dir)
            except ValueError:
                # scripts_dir was not in sys.path; nothing to do.
                pass
# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFetchLatestStatcast:
    """Tests for fetch_latest_statcast()."""

    def test_calls_statcast_with_yesterday(self):
        """fetch_latest_statcast must request yesterday's date."""
        pd_stub = _make_pandas_stub()
        mock_df = pd_stub.DataFrame([1, 2, 3])
        mock_df.empty = False
        pybaseball_stub = _make_pybaseball_stub(return_value=mock_df)

        mod = _import_module(pd_stub, pybaseball_stub)

        result = mod.fetch_latest_statcast()

        yesterday = date.today() - timedelta(days=1)
        expected_date_str = yesterday.strftime("%Y-%m-%d")
        pybaseball_stub.statcast.assert_called_once_with(
            start_dt=expected_date_str, end_dt=expected_date_str
        )
        assert result is mock_df

    def test_returns_dataframe(self):
        """fetch_latest_statcast must return the DataFrame from statcast()."""
        pd_stub = _make_pandas_stub()
        mock_df = pd_stub.DataFrame([1])
        mock_df.empty = False
        pybaseball_stub = _make_pybaseball_stub(return_value=mock_df)

        mod = _import_module(pd_stub, pybaseball_stub)
        result = mod.fetch_latest_statcast()

        assert result is mock_df


class TestMain:
    """Tests for main()."""

    def test_main_saves_csv_when_data_returned(self, tmp_path):
        """main() should write CSV when statcast returns non-empty data."""
        pd_stub = _make_pandas_stub()
        mock_df = pd_stub.DataFrame([{"col": 1}])
        mock_df.empty = False
        pybaseball_stub = _make_pybaseball_stub(return_value=mock_df)

        mod = _import_module(pd_stub, pybaseball_stub)

        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.object(mod, "OUTPUT_PATH", output_path):
            mod.main()

        assert os.path.exists(output_path)

    def test_main_writes_empty_csv_when_no_data(self, tmp_path):
        """main() should write an empty CSV when statcast returns empty data."""
        pd_stub = _make_pandas_stub()
        empty_df = pd_stub.DataFrame()  # empty=True
        pybaseball_stub = _make_pybaseball_stub(return_value=empty_df)

        mod = _import_module(pd_stub, pybaseball_stub)

        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.object(mod, "OUTPUT_PATH", output_path):
            mod.main()

        assert os.path.exists(output_path)

    def test_main_writes_empty_csv_when_none_returned(self, tmp_path):
        """main() should write an empty CSV when statcast returns None."""
        pd_stub = _make_pandas_stub()
        pybaseball_stub = _make_pybaseball_stub(return_value=None)

        mod = _import_module(pd_stub, pybaseball_stub)

        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.object(mod, "OUTPUT_PATH", output_path):
            mod.main()

        assert os.path.exists(output_path)

    def test_main_writes_empty_csv_when_fetch_raises(self, tmp_path):
        """main() should write an empty CSV and exit cleanly when fetch raises."""
        pd_stub = _make_pandas_stub()
        pybaseball_stub = _make_pybaseball_stub()
        pybaseball_stub.statcast.side_effect = ConnectionError("network unavailable")

        mod = _import_module(pd_stub, pybaseball_stub)

        output_path = str(tmp_path / "latest_statcast.csv")
        with patch.object(mod, "OUTPUT_PATH", output_path):
            mod.main()  # must not raise

        assert os.path.exists(output_path)


class TestOutputPath:
    """Tests for the module-level OUTPUT_PATH constant."""

    def test_output_path_ends_with_expected_suffix(self):
        """OUTPUT_PATH must point to data/latest_statcast.csv."""
        pd_stub = _make_pandas_stub()
        pybaseball_stub = _make_pybaseball_stub()

        mod = _import_module(pd_stub, pybaseball_stub)

        assert mod.OUTPUT_PATH.endswith(
            os.path.join("data", "latest_statcast.csv")
        )
