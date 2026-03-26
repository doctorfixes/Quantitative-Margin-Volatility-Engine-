"""
Tests for api/base44_client.py.

All network calls are mocked with unittest.mock — no live Base44 API calls are made.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from api.base44_client import (
    APP_ID,
    BASE_URL,
    MATCHUP_ENTITY,
    Base44AuthError,
    Base44Client,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY = "test-key-abc123"

SAMPLE_MATCHUP = {
    "signal": "BET",
    "reason": "Edge",
    "ba_gap": 10.0,
    "abs_edge": 2.0,
    "spread": -8.0,
    "ou": 138.0,
}

CREATED_MATCHUP = {"id": "m1", **SAMPLE_MATCHUP}


def _make_response(status: int, body: object) -> MagicMock:
    """Return a mock httpx.Response that raises on 4xx/5xx."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = body
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_client(resp: MagicMock) -> MagicMock:
    """Return a mock httpx.Client context manager that always returns *resp*."""
    http = MagicMock()
    http.__enter__ = MagicMock(return_value=http)
    http.__exit__ = MagicMock(return_value=False)
    http.get.return_value = resp
    http.post.return_value = resp
    http.put.return_value = resp
    http.delete.return_value = resp
    return http


# ---------------------------------------------------------------------------
# APP_ID / constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_app_id(self):
        assert APP_ID == "69c3204219e8e63b63a9e14e"

    def test_base_url_contains_app_id(self):
        assert APP_ID in BASE_URL

    def test_matchup_entity_name(self):
        assert MATCHUP_ENTITY == "Matchup"


# ---------------------------------------------------------------------------
# Auth / factory
# ---------------------------------------------------------------------------


class TestAuth:
    def test_empty_key_raises(self):
        with pytest.raises(Base44AuthError):
            Base44Client(api_key="")

    def test_from_env_missing_raises(self, monkeypatch):
        monkeypatch.delenv("BASE44_API_KEY", raising=False)
        with pytest.raises(Base44AuthError):
            Base44Client.from_env()

    def test_from_env_reads_variable(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", _API_KEY)
        client = Base44Client.from_env()
        assert client is not None

    def test_authorization_header_set(self):
        client = Base44Client(api_key=_API_KEY)
        assert client._headers["Authorization"] == f"Bearer {_API_KEY}"


# ---------------------------------------------------------------------------
# list_matchups
# ---------------------------------------------------------------------------


class TestListMatchups:
    def test_returns_list(self):
        http = _mock_client(_make_response(200, [CREATED_MATCHUP]))
        with patch("api.base44_client.httpx.Client", return_value=http):
            result = Base44Client(api_key=_API_KEY).list_matchups()
        assert isinstance(result, list)
        assert result[0]["id"] == "m1"

    def test_raises_on_error_status(self):
        http = _mock_client(_make_response(401, {"detail": "Unauthorized"}))
        with patch("api.base44_client.httpx.Client", return_value=http):
            with pytest.raises(httpx.HTTPStatusError):
                Base44Client(api_key=_API_KEY).list_matchups()

    def test_filters_forwarded(self):
        http = _mock_client(_make_response(200, []))
        with patch("api.base44_client.httpx.Client", return_value=http):
            Base44Client(api_key=_API_KEY).list_matchups(filters={"signal": "BET"})
        _, kwargs = http.get.call_args
        assert kwargs.get("params", {}).get("signal") == "BET"


# ---------------------------------------------------------------------------
# get_matchup
# ---------------------------------------------------------------------------


class TestGetMatchup:
    def test_returns_matchup(self):
        http = _mock_client(_make_response(200, CREATED_MATCHUP))
        with patch("api.base44_client.httpx.Client", return_value=http):
            result = Base44Client(api_key=_API_KEY).get_matchup("m1")
        assert result["id"] == "m1"
        assert result["signal"] == "BET"

    def test_raises_on_404(self):
        http = _mock_client(_make_response(404, {"detail": "Not found"}))
        with patch("api.base44_client.httpx.Client", return_value=http):
            with pytest.raises(httpx.HTTPStatusError):
                Base44Client(api_key=_API_KEY).get_matchup("nonexistent")


# ---------------------------------------------------------------------------
# create_matchup
# ---------------------------------------------------------------------------


class TestCreateMatchup:
    def test_returns_created_record(self):
        http = _mock_client(_make_response(200, CREATED_MATCHUP))
        with patch("api.base44_client.httpx.Client", return_value=http):
            result = Base44Client(api_key=_API_KEY).create_matchup(SAMPLE_MATCHUP)
        assert result["id"] == "m1"
        assert result["signal"] == "BET"

    def test_sends_correct_body(self):
        http = _mock_client(_make_response(200, CREATED_MATCHUP))
        with patch("api.base44_client.httpx.Client", return_value=http):
            Base44Client(api_key=_API_KEY).create_matchup(SAMPLE_MATCHUP)
        _, kwargs = http.post.call_args
        assert kwargs["json"]["signal"] == "BET"
        assert kwargs["json"]["abs_edge"] == 2.0

    def test_raises_on_error_status(self):
        http = _mock_client(_make_response(500, {"detail": "Server error"}))
        with patch("api.base44_client.httpx.Client", return_value=http):
            with pytest.raises(httpx.HTTPStatusError):
                Base44Client(api_key=_API_KEY).create_matchup(SAMPLE_MATCHUP)


# ---------------------------------------------------------------------------
# update_matchup
# ---------------------------------------------------------------------------


class TestUpdateMatchup:
    def test_returns_updated_record(self):
        updated = {**CREATED_MATCHUP, "signal": "PASS"}
        http = _mock_client(_make_response(200, updated))
        with patch("api.base44_client.httpx.Client", return_value=http):
            result = Base44Client(api_key=_API_KEY).update_matchup("m1", {"signal": "PASS"})
        assert result["signal"] == "PASS"

    def test_raises_on_error_status(self):
        http = _mock_client(_make_response(404, {"detail": "Not found"}))
        with patch("api.base44_client.httpx.Client", return_value=http):
            with pytest.raises(httpx.HTTPStatusError):
                Base44Client(api_key=_API_KEY).update_matchup("bad-id", {})


# ---------------------------------------------------------------------------
# delete_matchup
# ---------------------------------------------------------------------------


class TestDeleteMatchup:
    def test_succeeds_on_204(self):
        http = _mock_client(_make_response(204, None))
        with patch("api.base44_client.httpx.Client", return_value=http):
            result = Base44Client(api_key=_API_KEY).delete_matchup("m1")
        assert result is None

    def test_raises_on_error_status(self):
        http = _mock_client(_make_response(404, {"detail": "Not found"}))
        with patch("api.base44_client.httpx.Client", return_value=http):
            with pytest.raises(httpx.HTTPStatusError):
                Base44Client(api_key=_API_KEY).delete_matchup("nonexistent")


# ---------------------------------------------------------------------------
# FastAPI /classify integration — push to Base44 when key is set
# ---------------------------------------------------------------------------


class TestClassifyPushToBase44:
    """Verify that the FastAPI classify endpoint tries to push when API key set."""

    def test_classify_pushes_when_key_set(self, monkeypatch):
        from fastapi.testclient import TestClient
        from api.main import app

        pushed = []

        class _FakeClient:
            def create_matchup(self, data):
                pushed.append(data)
                return {"id": "x1", **data}

        monkeypatch.setenv("BASE44_API_KEY", _API_KEY)
        monkeypatch.setattr("api.main._get_base44_client", lambda: _FakeClient())

        with TestClient(app) as tc:
            resp = tc.post("/classify", json={
                "fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138
            })
        assert resp.status_code == 200
        assert len(pushed) == 1
        assert pushed[0]["signal"] == "BET"

    def test_classify_skips_push_when_key_absent(self, monkeypatch):
        from fastapi.testclient import TestClient
        from api.main import app

        monkeypatch.delenv("BASE44_API_KEY", raising=False)
        monkeypatch.setattr("api.main._get_base44_client", lambda: None)

        with TestClient(app) as tc:
            resp = tc.post("/classify", json={
                "fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138
            })
        assert resp.status_code == 200

    def test_classify_still_returns_result_if_push_fails(self, monkeypatch):
        from fastapi.testclient import TestClient
        from api.main import app

        class _FailClient:
            def create_matchup(self, data):
                raise httpx.HTTPError("network error")

        monkeypatch.setenv("BASE44_API_KEY", _API_KEY)
        monkeypatch.setattr("api.main._get_base44_client", lambda: _FailClient())

        with TestClient(app) as tc:
            resp = tc.post("/classify", json={
                "fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138
            })
        assert resp.status_code == 200
        assert resp.json()["signal"] == "BET"
