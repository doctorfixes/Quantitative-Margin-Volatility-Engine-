"""
Tests for api/main.py — AXIOM-60 FastAPI Base44 integration layer.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_body(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["engine"] == "AXIOM-60"


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_basic_metrics(self):
        payload = {"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 140}
        response = client.post("/metrics", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["ba_gap"] == 10.0
        assert data["abs_edge"] == 2.0

    def test_missing_field_returns_422(self):
        response = client.post("/metrics", json={"fav_adj_em": 22.0, "dog_adj_em": 12.0})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# /classify
# ---------------------------------------------------------------------------


class TestClassifySingle:
    def test_bet_signal(self):
        # abs_edge = |10 − 8| = 2.0 ≥ 1.5 → BET/Edge
        payload = {"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138}
        response = client.post("/classify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "BET"
        assert data["reason"] == "Edge"

    def test_live_dog_signal(self):
        # ba_gap=4, abs_edge=|4-5|=1.0, ba_gap(4) < |spread|(5)
        payload = {"fav_adj_em": 18.0, "dog_adj_em": 14.0, "spread": -5.0, "ou": 135}
        response = client.post("/classify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "BET"
        assert data["reason"] == "LIVE DOG"

    def test_tempo_pass(self):
        payload = {"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 155}
        response = client.post("/classify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "PASS"
        assert data["reason"] == "Tempo"

    def test_spreadcap_pass(self):
        payload = {"fav_adj_em": 30.0, "dog_adj_em": 5.0, "spread": -25.0, "ou": 140}
        response = client.post("/classify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "PASS"
        assert data["reason"] == "SpreadCap"

    def test_standard_pass(self):
        # ba_gap=3, abs_edge=|3-3|=0 → Standard PASS
        payload = {"fav_adj_em": 20.0, "dog_adj_em": 17.0, "spread": -3.0, "ou": 140}
        response = client.post("/classify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "PASS"
        assert data["reason"] == "Standard"

    def test_response_includes_all_fields(self):
        payload = {"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138}
        data = client.post("/classify", json=payload).json()
        for field in ("signal", "reason", "ba_gap", "abs_edge", "spread", "ou"):
            assert field in data

    def test_missing_field_returns_422(self):
        response = client.post("/classify", json={"fav_adj_em": 22.0})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# /classify/batch
# ---------------------------------------------------------------------------


class TestClassifyBatch:
    def test_batch_two_entries(self):
        payload = {
            "entries": [
                {"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138},
                {"fav_adj_em": 20.0, "dog_adj_em": 17.0, "spread": -3.0, "ou": 140},
            ]
        }
        response = client.post("/classify/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["signal"] == "BET"
        assert data["results"][1]["signal"] == "PASS"

    def test_batch_single_entry(self):
        payload = {
            "entries": [
                {"fav_adj_em": 22.0, "dog_adj_em": 12.0, "spread": -8.0, "ou": 138}
            ]
        }
        response = client.post("/classify/batch", json=payload)
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_empty_entries_returns_422(self):
        response = client.post("/classify/batch", json={"entries": []})
        assert response.status_code == 422

    def test_missing_entries_field_returns_422(self):
        response = client.post("/classify/batch", json={})
        assert response.status_code == 422
