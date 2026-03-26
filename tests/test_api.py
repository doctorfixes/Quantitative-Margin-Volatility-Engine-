"""
Tests for the AXIOM-60 FastAPI server.
Uses FastAPI's TestClient (wraps httpx) — no live server required.
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set the API key before importing the app so the module reads it correctly.
os.environ["AXIOM_API_KEY"] = "test-key"

from api.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)
auth_headers = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------

class TestHealthz:
    def test_healthz_returns_ok(self):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_healthz_no_auth_required(self):
        resp = client.get("/healthz", headers={})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /classify — auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_missing_key_returns_403(self):
        resp = client.post("/classify", json={
            "fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138.0,
        })
        assert resp.status_code == 403

    def test_wrong_key_returns_403(self):
        resp = client.post(
            "/classify",
            json={"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138.0},
            headers={"X-API-Key": "wrong"},
        )
        assert resp.status_code == 403

    def test_correct_key_is_accepted(self):
        resp = client.post(
            "/classify",
            json={"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /classify — correct results (mirrors scripts/axiom60 gate tests)
# ---------------------------------------------------------------------------

class TestClassifyEndpoint:
    def _post(self, fav_adj_em, dog_adj_em, spread, ou):
        resp = client.post(
            "/classify",
            json={
                "fav_adj_em": fav_adj_em,
                "dog_adj_em": dog_adj_em,
                "spread": spread,
                "ou": ou,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()

    def test_bet_edge(self):
        data = self._post(22.0, 12.0, -8.0, 138.0)
        assert data["signal"] == "BET"
        assert data["reason"] == "Edge"

    def test_pass_tempo(self):
        data = self._post(25.0, 15.0, -8.0, 152.0)
        assert data["signal"] == "PASS"
        assert data["reason"] == "Tempo"

    def test_pass_spread_cap(self):
        data = self._post(30.0, 5.0, -25.0, 140.0)
        assert data["signal"] == "PASS"
        assert data["reason"] == "SpreadCap"

    def test_bet_live_dog(self):
        data = self._post(18.0, 14.0, -5.0, 135.0)
        assert data["signal"] == "BET"
        assert data["reason"] == "LIVE DOG"

    def test_pass_standard(self):
        data = self._post(20.0, 17.0, -3.0, 140.0)
        assert data["signal"] == "PASS"
        assert data["reason"] == "Standard"

    def test_response_includes_metrics(self):
        data = self._post(22.0, 12.0, -8.0, 138.0)
        assert "ba_gap" in data
        assert "abs_edge" in data
        assert data["spread"] == pytest.approx(-8.0)
        assert data["ou"] == pytest.approx(138.0)


# ---------------------------------------------------------------------------
# /classify — validation
# ---------------------------------------------------------------------------

class TestClassifyValidation:
    def test_missing_field_returns_422(self):
        resp = client.post(
            "/classify",
            json={"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_non_numeric_field_returns_422(self):
        resp = client.post(
            "/classify",
            json={"fav_adj_em": "x", "dog_adj_em": 12.0, "spread": -8.0, "ou": 138.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422
