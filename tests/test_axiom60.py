"""
AXIOM-60 Filter Chain — Validation Tests
Covers every gate + boundary edge cases.
"""
from scripts.axiom60 import classify, compute_metrics


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
