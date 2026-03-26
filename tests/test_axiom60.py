"""
AXIOM-60 Filter Chain — Validation Tests
Covers every gate + boundary edge cases.
"""
import pytest
from scripts.axiom60 import (
    REGIME_DECAY,
    apply_regime_decay,
    classify,
    cleanup_tickers,
    compute_metrics,
    register_ticker,
)


# -- Metric computation --

class TestMetrics:
    def test_ba_gap_calculation(self):
        result = compute_metrics(22.0, 12.0, -8.0)
        assert result["ba_gap"] == 10.0

    def test_abs_edge_calculation(self):
        result = compute_metrics(22.0, 12.0, -8.0)
        assert result["abs_edge"] == 2.0

    def test_zero_gap(self):
        result = compute_metrics(15.0, 15.0, -5.0)
        assert result["ba_gap"] == 0.0
        assert result["abs_edge"] == 5.0


# -- Gate 1: Tempo filter --

class TestTempoGate:
    def test_ou_above_148_is_tempo_pass(self):
        result = classify(25.0, 15.0, -8.0, 152)
        assert result["signal"] == "PASS"
        assert result["reason"] == "Tempo"

    def test_ou_exactly_148_does_not_trigger(self):
        """O/U must be strictly > 148"""
        result = classify(25.0, 15.0, -8.0, 148)
        assert result["reason"] != "Tempo"

    def test_ou_148_point_1_triggers(self):
        result = classify(25.0, 15.0, -8.0, 148.1)
        assert result["reason"] == "Tempo"


# -- Gate 2: SpreadCap filter --

class TestSpreadCapGate:
    def test_spread_above_24_5_is_cap_pass(self):
        result = classify(30.0, 5.0, -25.0, 140)
        assert result["signal"] == "PASS"
        assert result["reason"] == "SpreadCap"

    def test_spread_exactly_24_5_does_not_trigger(self):
        """|Spread| must be strictly > 24.5"""
        result = classify(30.0, 5.0, -24.5, 140)
        assert result["reason"] != "SpreadCap"

    def test_positive_spread_above_cap(self):
        result = classify(30.0, 5.0, 25.0, 140)
        assert result["reason"] == "SpreadCap"


# -- Gate 3: BET --

class TestBetGate:
    def test_abs_edge_above_1_5_is_bet(self):
        result = classify(22.0, 12.0, -8.0, 138)
        assert result["signal"] == "BET"
        assert result["reason"] == "Edge"

    def test_abs_edge_exactly_1_5_triggers(self):
        """Threshold is >= 1.5"""
        result = classify(20.0, 13.5, -5.0, 140)
        # ba_gap=6.5, abs_edge=|6.5-5.0|=1.5
        assert result["signal"] == "BET"
        assert result["reason"] == "Edge"

    def test_abs_edge_1_49_does_not_trigger_bet(self):
        result = classify(20.0, 14.51, -4.0, 140)
        # ba_gap=5.49, abs_edge=|5.49-4.0|=1.49
        assert result["reason"] != "Edge"


# -- Gate 4: LIVE DOG --

class TestLiveDogGate:
    def test_live_dog_triggers(self):
        result = classify(18.0, 14.0, -5.0, 135)
        # ba_gap=4.0, abs_edge=|4.0-5.0|=1.0, ba_gap(4) < |spread|(5)
        assert result["signal"] == "BET"
        assert result["reason"] == "LIVE DOG"

    def test_abs_edge_1_0_but_not_dog_aligned(self):
        """abs_edge >= 1.0 but ba_gap >= |spread| → no LIVE DOG"""
        result = classify(22.0, 16.0, -5.0, 140)
        # ba_gap=6.0, abs_edge=|6.0-5.0|=1.0, ba_gap(6) >= |spread|(5)
        assert result["reason"] != "LIVE DOG"

    def test_abs_edge_below_1_0_no_live_dog(self):
        result = classify(18.0, 14.5, -4.0, 140)
        # ba_gap=3.5, abs_edge=|3.5-4.0|=0.5
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"


# -- Gate 5: Standard PASS --

class TestStandardPass:
    def test_no_edge_is_pass(self):
        result = classify(20.0, 17.0, -3.0, 140)
        # ba_gap=3.0, abs_edge=|3.0-3.0|=0.0
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"


# -- Gate priority (Tempo overrides everything) --

class TestGatePriority:
    def test_tempo_overrides_bet_edge(self):
        """Even with abs_edge >= 1.5, Tempo fires first"""
        result = classify(22.0, 12.0, -8.0, 155)
        assert result["reason"] == "Tempo"

    def test_spreadcap_overrides_bet(self):
        """Even with huge edge, SpreadCap fires first"""
        result = classify(40.0, 5.0, -26.0, 130)
        assert result["reason"] == "SpreadCap"


# -- Regime Decay (0.97x) --

class TestRegimeDecay:
    def test_regime_decay_constant(self):
        assert REGIME_DECAY == 0.97

    def test_apply_regime_decay(self):
        assert apply_regime_decay(20.0) == pytest.approx(19.4)

    def test_tournament_regime_shrinks_ba_gap(self):
        """AdjEM values are scaled by 0.97 before computing metrics."""
        base = classify(22.0, 12.0, -8.0, 138)
        regime = classify(22.0, 12.0, -8.0, 138, tournament_regime=True)
        # decayed ba_gap = (22*0.97 - 12*0.97) = 10*0.97 = 9.7
        assert regime["ba_gap"] == pytest.approx(9.7)
        assert regime["ba_gap"] < base["ba_gap"]

    def test_tournament_regime_false_by_default(self):
        """Default behavior is unchanged when tournament_regime is omitted."""
        result_default = classify(22.0, 12.0, -8.0, 138)
        result_explicit = classify(22.0, 12.0, -8.0, 138, tournament_regime=False)
        assert result_default == result_explicit

    def test_regime_decay_can_flip_classification(self):
        """Decay reducing abs_edge below 1.5 threshold changes BET/Edge → PASS/Standard."""
        # Without decay: ba_gap=6.5, abs_edge=|6.5-5.0|=1.5 → BET/Edge
        base = classify(20.0, 13.5, -5.0, 140)
        assert base["signal"] == "BET"
        assert base["reason"] == "Edge"
        # With decay: fav=19.4, dog=13.095, ba_gap=6.305, abs_edge=|6.305-5.0|=1.305 → PASS/Standard
        # ba_gap(6.305) >= |spread|(5.0) so LIVE DOG doesn't fire either
        regime = classify(20.0, 13.5, -5.0, 140, tournament_regime=True)
        assert regime["signal"] == "PASS"
        assert regime["reason"] == "Standard"


# -- Ticker Memory Cleanup --

class TestTickerMemory:
    def setup_method(self):
        """Ensure a clean slate before every test."""
        cleanup_tickers()

    def test_register_and_cleanup(self):
        result = classify(22.0, 12.0, -8.0, 138)
        register_ticker("TEAM_A_vs_TEAM_B", result)
        removed = cleanup_tickers()
        assert removed == 1

    def test_cleanup_returns_zero_when_empty(self):
        assert cleanup_tickers() == 0

    def test_cleanup_removes_multiple_tickers(self):
        register_ticker("GAME1", {"signal": "BET"})
        register_ticker("GAME2", {"signal": "PASS"})
        register_ticker("GAME3", {"signal": "BET"})
        removed = cleanup_tickers()
        assert removed == 3
        # Memory is now empty
        assert cleanup_tickers() == 0

    def test_register_ticker_overwrites_same_key(self):
        register_ticker("GAME1", {"signal": "BET"})
        register_ticker("GAME1", {"signal": "PASS"})
        removed = cleanup_tickers()
        assert removed == 1


# -- Null-Safe AdjEM Handling --

class TestNullAdjEM:
    def test_compute_metrics_null_fav(self):
        result = compute_metrics(None, 12.0, -8.0)
        assert result["ba_gap"] is None
        assert result["abs_edge"] is None

    def test_compute_metrics_null_dog(self):
        result = compute_metrics(22.0, None, -8.0)
        assert result["ba_gap"] is None
        assert result["abs_edge"] is None

    def test_compute_metrics_both_null(self):
        result = compute_metrics(None, None, -8.0)
        assert result["ba_gap"] is None
        assert result["abs_edge"] is None

    def test_classify_null_fav_returns_pass(self):
        result = classify(None, 12.0, -8.0, 138)
        assert result["signal"] == "PASS"
        assert result["reason"] == "NullAdjEM"

    def test_classify_null_dog_returns_pass(self):
        result = classify(22.0, None, -8.0, 138)
        assert result["signal"] == "PASS"
        assert result["reason"] == "NullAdjEM"

    def test_classify_null_preserves_spread_and_ou(self):
        result = classify(None, None, -9.5, 145)
        assert result["spread"] == -9.5
        assert result["ou"] == 145

    def test_classify_null_with_tournament_regime(self):
        """Null guard fires before regime decay is applied."""
        result = classify(None, 12.0, -8.0, 138, tournament_regime=True)
        assert result["signal"] == "PASS"
        assert result["reason"] == "NullAdjEM"
