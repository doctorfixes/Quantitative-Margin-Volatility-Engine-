"""
Tests for the Sweet 16 slate, lib.axiom60 wrapper, and SelectionDash.
"""
import pytest

from data.sweet16 import live_tournament_slate
from lib.axiom60 import run_axiom60
from scripts.axiom60 import classify
from selection_dash import SelectionDash


# ---------------------------------------------------------------------------
# data.sweet16
# ---------------------------------------------------------------------------

class TestSweetSixteenSlate:
    REQUIRED_KEYS = {"game_id", "region", "favorite", "underdog",
                     "fav_adj_em", "dog_adj_em", "spread", "ou"}

    def test_slate_has_sixteen_teams(self):
        """Sweet 16 = 8 games."""
        assert len(live_tournament_slate) == 8

    def test_all_games_have_required_keys(self):
        for game in live_tournament_slate:
            missing = self.REQUIRED_KEYS - game.keys()
            assert not missing, f"{game['game_id']} missing keys: {missing}"

    def test_game_ids_are_unique(self):
        ids = [g["game_id"] for g in live_tournament_slate]
        assert len(ids) == len(set(ids))

    def test_four_regions_represented(self):
        regions = {g["region"] for g in live_tournament_slate}
        assert regions == {"East", "West", "South", "Midwest"}

    def test_spreads_are_negative(self):
        """Spread convention: negative = favorite lays points."""
        for game in live_tournament_slate:
            assert game["spread"] < 0, (
                f"{game['game_id']} spread should be negative, got {game['spread']}"
            )

    def test_ou_in_realistic_range(self):
        for game in live_tournament_slate:
            assert 120 <= game["ou"] <= 155, (
                f"{game['game_id']} O/U {game['ou']} outside realistic range"
            )


# ---------------------------------------------------------------------------
# lib.axiom60 — run_axiom60 wrapper
# ---------------------------------------------------------------------------

class TestRunAxiom60Wrapper:
    _sample_game = {
        "fav_adj_em": 22.0,
        "dog_adj_em": 12.0,
        "spread": -8.0,
        "ou": 138.0,
        "favorite": "TeamA",
        "underdog": "TeamB",
    }

    def test_returns_dict(self):
        result = run_axiom60(self._sample_game)
        assert isinstance(result, dict)

    def test_result_has_signal_and_reason(self):
        result = run_axiom60(self._sample_game)
        assert "signal" in result
        assert "reason" in result

    def test_agrees_with_classify(self):
        game = self._sample_game
        expected = classify(
            game["fav_adj_em"], game["dog_adj_em"], game["spread"], game["ou"]
        )
        assert run_axiom60(game) == expected

    def test_extra_keys_in_game_dict_are_ignored(self):
        """run_axiom60 must not raise when extra metadata keys are present."""
        game = {**self._sample_game, "region": "East", "game_id": "X1"}
        result = run_axiom60(game)
        assert result["signal"] in ("BET", "PASS")

    def test_missing_required_key_raises(self):
        bad_game = {"fav_adj_em": 20.0, "dog_adj_em": 10.0, "spread": -5.0}
        with pytest.raises(KeyError):
            run_axiom60(bad_game)


# ---------------------------------------------------------------------------
# SelectionDash
# ---------------------------------------------------------------------------

class TestSelectionDash:
    def test_returns_list(self):
        assert isinstance(SelectionDash(), list)

    def test_length_matches_slate(self):
        assert len(SelectionDash()) == len(live_tournament_slate)

    def test_each_entry_has_result_key(self):
        for entry in SelectionDash():
            assert "result" in entry, f"{entry['game_id']} missing 'result'"

    def test_original_game_fields_preserved(self):
        for original, processed in zip(live_tournament_slate, SelectionDash()):
            for key in original:
                assert processed[key] == original[key]

    def test_result_signals_are_valid(self):
        for entry in SelectionDash():
            assert entry["result"]["signal"] in ("BET", "PASS"), (
                f"{entry['game_id']} has unexpected signal: {entry['result']['signal']}"
            )

    def test_no_game_exceeds_tempo_threshold(self):
        """All Sweet 16 O/U values are <= 148 so Tempo gate should not fire."""
        for entry in SelectionDash():
            assert entry["result"]["reason"] != "Tempo", (
                f"{entry['game_id']} unexpectedly hit Tempo gate"
            )
