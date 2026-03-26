"""
AXIOM-60 Filter Chain — Validation Tests
Covers every gate + boundary edge cases.
Patch 2.6.1: updated for dual efficiency sources, regime decay (0.97), and strength output.
"""
from scripts.axiom60 import classify, compute_metrics, REGIME_DECAY


# -- Metric computation --

class TestMetrics:
    def test_ba_gap_calculation(self):
        # Same KP and TV values → ba_gap equals simple difference
        result = compute_metrics(22.0, 12.0, 22.0, 12.0, -8.0)
        assert result["ba_gap"] == 10.0

    def test_abs_edge_calculation(self):
        result = compute_metrics(22.0, 12.0, 22.0, 12.0, -8.0)
        assert result["abs_edge"] == 2.0

    def test_zero_gap(self):
        result = compute_metrics(15.0, 15.0, 15.0, 15.0, -5.0)
        assert result["ba_gap"] == 0.0
        assert result["abs_edge"] == 5.0

    def test_dual_metric_averaging(self):
        """KP gap and TV gap are averaged for ba_gap"""
        # KP gap = 10.0, TV gap = 14.0 → average = 12.0
        result = compute_metrics(20.0, 10.0, 24.0, 10.0, -8.0)
        assert result["ba_gap"] == 12.0
        assert result["abs_edge"] == abs(12.0 - 8.0)

    def test_dual_metric_different_sources(self):
        """Different KP and TV values are properly averaged"""
        result = compute_metrics(20.0, 10.0, 22.0, 10.0, -8.0)
        # KP gap = 10.0, TV gap = 12.0 → average = 11.0
        assert result["ba_gap"] == 11.0
        assert result["abs_edge"] == 3.0


# -- Gate 1: Tempo filter --

class TestTempoGate:
    def test_ou_above_effective_threshold_is_tempo_pass(self):
        # Effective threshold: ou > 148 / 0.97 ~= 152.58; ou=154 -> adj_ou=149.38 > 148
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 154)
        assert result["signal"] == "PASS"
        assert result["reason"] == "Tempo"

    def test_ou_exactly_148_does_not_trigger(self):
        """adj_ou = ou * 0.97; ou=148 -> adj_ou=143.56 <= 148 -> no Tempo"""
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 148)
        assert result["reason"] != "Tempo"

    def test_ou_just_over_effective_threshold_triggers(self):
        """ou=152.7 -> adj_ou~=148.12 > 148 -> Tempo fires"""
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 152.7)
        assert result["reason"] == "Tempo"


# -- Gate 2: SpreadCap filter --

class TestSpreadCapGate:
    def test_spread_above_24_5_is_cap_pass(self):
        result = classify(30.0, 5.0, 30.0, 5.0, -25.0, 140)
        assert result["signal"] == "PASS"
        assert result["reason"] == "SpreadCap"

    def test_spread_exactly_24_5_does_not_trigger(self):
        """|Spread| must be strictly > 24.5"""
        result = classify(30.0, 5.0, 30.0, 5.0, -24.5, 140)
        assert result["reason"] != "SpreadCap"

    def test_positive_spread_above_cap(self):
        result = classify(30.0, 5.0, 30.0, 5.0, 25.0, 140)
        assert result["reason"] == "SpreadCap"


# -- Gate 3: BET --

class TestBetGate:
    def test_abs_edge_above_1_5_is_bet(self):
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["signal"] == "BET"
        assert result["reason"] == "Edge"

    def test_abs_edge_exactly_1_5_triggers(self):
        """Threshold is >= 1.5"""
        result = classify(20.0, 13.5, 20.0, 13.5, -5.0, 140)
        # ba_gap=6.5, abs_edge=|6.5-5.0|=1.5
        assert result["signal"] == "BET"
        assert result["reason"] == "Edge"

    def test_abs_edge_1_49_does_not_trigger_bet(self):
        result = classify(20.0, 14.51, 20.0, 14.51, -4.0, 140)
        # ba_gap=5.49, abs_edge=|5.49-4.0|=1.49
        assert result["reason"] != "Edge"


# -- Gate 4: LIVE DOG --

class TestLiveDogGate:
    def test_live_dog_triggers(self):
        result = classify(18.0, 14.0, 18.0, 14.0, -5.0, 135)
        # ba_gap=4.0, abs_edge=|4.0-5.0|=1.0, ba_gap(4) < |spread|(5)
        assert result["signal"] == "BET"
        assert result["reason"] == "LIVE DOG"

    def test_abs_edge_1_0_but_not_dog_aligned(self):
        """abs_edge >= 1.0 but ba_gap >= |spread| → no LIVE DOG"""
        result = classify(22.0, 16.0, 22.0, 16.0, -5.0, 140)
        # ba_gap=6.0, abs_edge=|6.0-5.0|=1.0, ba_gap(6) >= |spread|(5)
        assert result["reason"] != "LIVE DOG"

    def test_abs_edge_below_1_0_no_live_dog(self):
        result = classify(18.0, 14.5, 18.0, 14.5, -4.0, 140)
        # ba_gap=3.5, abs_edge=|3.5-4.0|=0.5
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"


# -- Gate 5: Standard PASS --

class TestStandardPass:
    def test_no_edge_is_pass(self):
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        # ba_gap=3.0, abs_edge=|3.0-3.0|=0.0
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"


# -- Gate priority (Tempo overrides everything) --

class TestGatePriority:
    def test_tempo_overrides_bet_edge(self):
        """Even with abs_edge >= 1.5, Tempo fires first"""
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 155)
        # adj_ou = 150.35 > 148 → Tempo
        assert result["reason"] == "Tempo"

    def test_spreadcap_overrides_bet(self):
        """Even with huge edge, SpreadCap fires first"""
        result = classify(40.0, 5.0, 40.0, 5.0, -26.0, 130)
        assert result["reason"] == "SpreadCap"


# -- Regime decay and strength output (Patch 2.6.1) --

class TestRegimeDecayAndStrength:
    def test_adj_ou_in_output(self):
        """adj_ou = ou * REGIME_DECAY is present in the result"""
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["adj_ou"] == round(138 * REGIME_DECAY, 4)

    def test_bet_has_positive_strength(self):
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["strength"] > 0

    def test_pass_has_zero_strength(self):
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        assert result["strength"] == 0

    def test_tempo_pass_has_zero_strength(self):
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 154)
        assert result["strength"] == 0

    def test_strength_capped_at_99_9(self):
        """Extreme abs_edge must cap strength at 99.9"""
        result = classify(50.0, 0.0, 50.0, 0.0, -1.0, 100)
        # ba_gap=50, abs_edge=49, adj_ou=97 → strength=min(99.9, 49*12.5+51)=99.9
        assert result["strength"] <= 99.9
        assert result["strength"] == 99.9

    def test_strength_formula_for_bet(self):
        """strength = min(99.9, abs_edge * 12.5 + (148 − adj_ou))"""
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        adj_ou = round(138 * REGIME_DECAY, 4)
        expected = min(99.9, result["abs_edge"] * 12.5 + (148 - adj_ou))
        assert result["strength"] == round(expected, 4)
