"""
AXIOM-60 API Tests
"""
import os

os.environ["AXIOM_API_KEY"] = "test-key-123"

from fastapi.testclient import TestClient  # noqa: E402
from scripts.api import app  # noqa: E402

client = TestClient(app)
AUTH_HEADERS = {"x-api-key": "test-key-123"}


class TestHealth:
    def test_ok(self):
        assert client.get("/health").status_code == 200


class TestAuth:
    def test_no_key(self):
        r = client.post(
            "/classify",
            json={"fav_adj_em": 22, "dog_adj_em": 12, "spread": -8, "ou": 138},
        )
        assert r.status_code == 401

    def test_wrong_key(self):
        r = client.post(
            "/classify",
            json={"fav_adj_em": 22, "dog_adj_em": 12, "spread": -8, "ou": 138},
            headers={"x-api-key": "wrong"},
        )
        assert r.status_code == 401

    def test_valid(self):
        r = client.post(
            "/classify",
            json={"fav_adj_em": 22, "dog_adj_em": 12, "spread": -8, "ou": 138},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200


class TestClassify:
    def test_bet(self):
        r = client.post(
            "/classify",
            json={"fav_adj_em": 22, "dog_adj_em": 12, "spread": -8, "ou": 138},
            headers=AUTH_HEADERS,
        )
        assert r.json()["signal"] == "BET"

    def test_live_dog(self):
        r = client.post(
            "/classify",
            json={"fav_adj_em": 18, "dog_adj_em": 14, "spread": -5, "ou": 135},
            headers=AUTH_HEADERS,
        )
        assert r.json()["reason"] == "LIVE DOG"


class TestBatch:
    def test_batch(self):
        r = client.post(
            "/classify/batch",
            json={
                "matchups": [
                    {"fav_adj_em": 22, "dog_adj_em": 12, "spread": -8, "ou": 138},
                    {"fav_adj_em": 25, "dog_adj_em": 15, "spread": -8, "ou": 152},
                ]
            },
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2

    def test_empty(self):
        r = client.post("/classify/batch", json={"matchups": []}, headers=AUTH_HEADERS)
        assert r.status_code == 422


class TestMetrics:
    def test_ok(self):
        r = client.post(
            "/metrics",
            json={"fav_adj_em": 22, "dog_adj_em": 12, "spread": -8},
            headers=AUTH_HEADERS,
        )
        assert r.json()["ba_gap"] == 10.0


class TestValidation:
    def test_missing(self):
        r = client.post(
            "/classify",
            json={"fav_adj_em": 22, "spread": -8, "ou": 138},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 422
