"""
Tournament Slate — Validation Tests
Verifies LIVE_TOURNAMENT_SLATE structure and AXIOM-60 signal output for
every Sweet-16 game.

Expected engine results (favTV / dogTV used as fav_adj_em / dog_adj_em):

  S16_01  Purdue -7.5  OU 147.5  ba_gap=8.7   abs_edge=1.2  → PASS / Standard
  S16_02  Nebraska -1.5 OU 131.5 ba_gap=2.5   abs_edge=1.0  → PASS / Standard
  S16_03  Houston -2.5  OU 139.5 ba_gap=8.3   abs_edge=5.8  → BET  / Edge
  S16_04  Arizona -8.5  OU 164.5 ou>148                     → PASS / Tempo
"""

import pytest
from scripts.tournament_slate import LIVE_TOURNAMENT_SLATE, run_slate


# ---------------------------------------------------------------------------
# Slate data structure
# ---------------------------------------------------------------------------

class TestSlateStructure:
    REQUIRED_KEYS = {"id", "fav", "dog", "spread", "ou",
                     "favKP", "dogKP", "favTV", "dogTV"}

    def test_slate_has_four_entries(self):
        assert len(LIVE_TOURNAMENT_SLATE) == 4

    def test_all_entries_have_required_keys(self):
        for game in LIVE_TOURNAMENT_SLATE:
            assert self.REQUIRED_KEYS.issubset(game.keys()), (
                f"Game {game.get('id')} missing keys"
            )

    def test_ids_are_unique(self):
        ids = [g["id"] for g in LIVE_TOURNAMENT_SLATE]
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("game", LIVE_TOURNAMENT_SLATE)
    def test_spreads_are_negative(self, game):
        """All favorites carry a negative spread."""
        assert game["spread"] < 0, f"{game['id']}: spread should be negative"

    @pytest.mark.parametrize("game", LIVE_TOURNAMENT_SLATE)
    def test_efficiency_values_are_positive(self, game):
        assert game["favTV"] > 0
        assert game["dogTV"] > 0
        assert game["favKP"] > 0
        assert game["dogKP"] > 0


# ---------------------------------------------------------------------------
# run_slate output shape
# ---------------------------------------------------------------------------

class TestRunSlate:
    def setup_method(self):
        self.results = run_slate()

    def test_returns_four_results(self):
        assert len(self.results) == 4

    def test_each_result_has_signal_and_reason(self):
        for r in self.results:
            assert "signal" in r
            assert "reason" in r

    def test_original_fields_preserved(self):
        for r in self.results:
            assert "fav" in r
            assert "dog" in r
            assert "spread" in r
            assert "ou" in r


# ---------------------------------------------------------------------------
# Per-game signal assertions
# ---------------------------------------------------------------------------

class TestGameSignals:
    def setup_method(self):
        self.by_id = {r["id"]: r for r in run_slate()}

    def test_s16_01_purdue_texas_standard_pass(self):
        """ba_gap=8.7, abs_edge=1.2 → below Edge threshold, ba_gap≥spread → Standard PASS"""
        r = self.by_id["S16_01"]
        assert r["signal"] == "PASS"
        assert r["reason"] == "Standard"
        assert r["ba_gap"] == pytest.approx(8.7)
        assert r["abs_edge"] == pytest.approx(1.2)

    def test_s16_02_nebraska_iowa_standard_pass(self):
        """ba_gap=2.5, abs_edge=1.0 → abs_edge≥1.0 but ba_gap≥|spread| → Standard PASS"""
        r = self.by_id["S16_02"]
        assert r["signal"] == "PASS"
        assert r["reason"] == "Standard"
        assert r["ba_gap"] == pytest.approx(2.5)
        assert r["abs_edge"] == pytest.approx(1.0)

    def test_s16_03_houston_illinois_bet_edge(self):
        """ba_gap=8.3, abs_edge=5.8 → abs_edge≥1.5 → BET / Edge"""
        r = self.by_id["S16_03"]
        assert r["signal"] == "BET"
        assert r["reason"] == "Edge"
        assert r["ba_gap"] == pytest.approx(8.3)
        assert r["abs_edge"] == pytest.approx(5.8)

    def test_s16_04_arizona_arkansas_tempo_pass(self):
        """O/U=164.5 > 148 → Tempo PASS fires first"""
        r = self.by_id["S16_04"]
        assert r["signal"] == "PASS"
        assert r["reason"] == "Tempo"
        assert r["ou"] == 164.5


# ---------------------------------------------------------------------------
# Custom slate support
# ---------------------------------------------------------------------------

class TestCustomSlate:
    def test_run_slate_accepts_custom_input(self):
        custom = [{
            "id": "TEST_01",
            "fav": "TeamA",
            "dog": "TeamB",
            "spread": -5.0,
            "ou": 140.0,
            "favKP": 20.0,
            "dogKP": 14.0,
            "favTV": 22.0,
            "dogTV": 12.0,
        }]
        results = run_slate(custom)
        assert len(results) == 1
        # ba_gap=10.0, abs_edge=|10-5|=5.0 → BET / Edge
        assert results[0]["signal"] == "BET"
        assert results[0]["reason"] == "Edge"
