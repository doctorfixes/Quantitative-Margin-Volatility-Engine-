"""
Base44 Client — Unit Tests
Uses monkeypatching to avoid real network calls.
"""
import json

import pytest

from api.base44_client import Base44Client, Base44Error


class FakeResponse:
    """Minimal fake for urllib.request.urlopen context manager."""

    def __init__(self, payload):
        self._data = json.dumps(payload).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# -- Initialisation --

class TestInit:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("BASE44_API_KEY", raising=False)
        with pytest.raises(Base44Error, match="BASE44_API_KEY"):
            Base44Client()

    def test_accepts_explicit_api_key(self):
        client = Base44Client(api_key="test-key")
        assert client._api_key == "test-key"

    def test_reads_env_api_key(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "env-key")
        client = Base44Client()
        assert client._api_key == "env-key"

    def test_explicit_key_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "env-key")
        client = Base44Client(api_key="explicit-key")
        assert client._api_key == "explicit-key"


# -- list_matchups --

class TestListMatchups:
    def test_returns_list_directly(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "test-key")
        client = Base44Client()
        matchups = [{"id": "1", "home": "Duke", "away": "UNC"}]

        monkeypatch.setattr("api.base44_client.urlopen", lambda req: FakeResponse(matchups))
        assert client.list_matchups() == matchups

    def test_unwraps_items_key(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "test-key")
        client = Base44Client()
        payload = {"items": [{"id": "2"}]}

        monkeypatch.setattr("api.base44_client.urlopen", lambda req: FakeResponse(payload))
        assert client.list_matchups() == [{"id": "2"}]

    def test_unwraps_data_key(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "test-key")
        client = Base44Client()
        payload = {"data": [{"id": "3"}]}

        monkeypatch.setattr("api.base44_client.urlopen", lambda req: FakeResponse(payload))
        assert client.list_matchups() == [{"id": "3"}]


# -- get_matchup --

class TestGetMatchup:
    def test_returns_entity(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "test-key")
        client = Base44Client()
        entity = {"id": "abc", "home": "Kansas", "away": "Baylor"}

        def fake_urlopen(req):
            assert "abc" in req.full_url
            return FakeResponse(entity)

        monkeypatch.setattr("api.base44_client.urlopen", fake_urlopen)
        result = client.get_matchup("abc")
        assert result == entity


# -- push_result --

class TestPushResult:
    def test_uses_patch_method(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "test-key")
        client = Base44Client()
        called = {}

        def fake_urlopen(req):
            called["method"] = req.get_method()
            called["url"] = req.full_url
            return FakeResponse({"ok": True})

        monkeypatch.setattr("api.base44_client.urlopen", fake_urlopen)
        client.push_result("abc123", {"signal": "BET"})
        assert called["method"] == "PATCH"
        assert "abc123" in called["url"]

    def test_returns_response_payload(self, monkeypatch):
        monkeypatch.setenv("BASE44_API_KEY", "test-key")
        client = Base44Client()

        monkeypatch.setattr("api.base44_client.urlopen", lambda req: FakeResponse({"ok": True}))
        result = client.push_result("xyz", {"signal": "PASS"})
        assert result == {"ok": True}
