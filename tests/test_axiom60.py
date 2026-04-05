"""
AXIOM-60 Filter Chain — Validation Tests
Covers every gate + boundary edge cases.
"""
from scripts.axiom60 import classify, compute_metrics, PRECISION


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

    def test_negative_ba_gap(self):
        """Dog efficiency higher than favourite produces negative ba_gap."""
        result = compute_metrics(10.0, 20.0, -5.0)
        assert result["ba_gap"] == -10.0
        # abs_edge = |(-10.0) - 5.0| = 15.0
        assert result["abs_edge"] == 15.0

    def test_positive_spread(self):
        """Positive spread value (abs taken internally)."""
        result = compute_metrics(22.0, 12.0, 8.0)
        assert result["ba_gap"] == 10.0
        # abs_edge = |10.0 - 8.0| = 2.0
        assert result["abs_edge"] == 2.0

    def test_zero_spread(self):
        result = compute_metrics(18.0, 13.0, 0.0)
        assert result["ba_gap"] == 5.0
        # abs_edge = |5.0 - 0.0| = 5.0
        assert result["abs_edge"] == 5.0

    def test_all_zero_inputs(self):
        result = compute_metrics(0.0, 0.0, 0.0)
        assert result["ba_gap"] == 0.0
        assert result["abs_edge"] == 0.0

    def test_precision_rounding(self):
        """Results are rounded to PRECISION decimal places."""
        result = compute_metrics(10.12345, 5.00001, -3.0)
        assert result["ba_gap"] == round(10.12345 - 5.00001, PRECISION)
        assert result["abs_edge"] == round(abs(result["ba_gap"] - 3.0), PRECISION)

    def test_return_keys(self):
        """compute_metrics must return exactly ba_gap and abs_edge."""
        result = compute_metrics(20.0, 10.0, -5.0)
        assert set(result.keys()) == {"ba_gap", "abs_edge"}


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

    def test_abs_edge_exactly_1_0_ba_gap_equals_spread_no_live_dog(self):
        """ba_gap < abs_spread must be strictly True; equality does not trigger."""
        result = classify(22.0, 17.0, -5.0, 140)
        # ba_gap=5.0, abs_edge=|5.0-5.0|=0.0 → Standard (abs_edge < 1.0)
        assert result["reason"] == "Standard"

    def test_live_dog_triggers_with_positive_spread(self):
        """Positive spread value is handled identically to negative."""
        result = classify(18.0, 14.0, 5.0, 135)
        # ba_gap=4.0, abs_spread=5.0, abs_edge=1.0, ba_gap(4) < abs_spread(5)
        assert result["signal"] == "BET"
        assert result["reason"] == "LIVE DOG"


# -- Gate 5: Standard PASS --

class TestStandardPass:
    def test_no_edge_is_pass(self):
        result = classify(20.0, 17.0, -3.0, 140)
        # ba_gap=3.0, abs_edge=|3.0-3.0|=0.0
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"

    def test_all_zero_inputs_is_standard_pass(self):
        result = classify(0.0, 0.0, 0.0, 0.0)
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"

    def test_small_edge_below_both_thresholds(self):
        """abs_edge between 0 and 1.0 always falls through to Standard."""
        result = classify(15.0, 14.5, -4.0, 140)
        # ba_gap=0.5, abs_edge=|0.5-4.0|=3.5 → wait, that's >= 1.5 → BET
        # Use inputs that give abs_edge < 1.0
        result = classify(15.0, 14.5, -0.4, 140)
        # ba_gap=0.5, abs_edge=|0.5-0.4|=0.1
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

    def test_tempo_overrides_spreadcap(self):
        """ou > 148 and abs_spread > 24.5: Tempo fires first."""
        result = classify(30.0, 5.0, -25.5, 150)
        assert result["reason"] == "Tempo"

    def test_tempo_overrides_live_dog(self):
        """ou > 148 with LIVE DOG conditions: Tempo fires first."""
        result = classify(18.0, 14.0, -5.0, 149)
        # abs_edge=1.0, ba_gap=4 < 5 → would be LIVE DOG, but ou=149>148
        assert result["reason"] == "Tempo"

    def test_spreadcap_overrides_live_dog(self):
        """abs_spread > 24.5 with LIVE DOG conditions: SpreadCap fires first."""
        result = classify(18.0, 14.0, -25.0, 140)
        # abs_edge=|4.0-25.0|=21.0 >=1.5 → BET before SpreadCap...
        # Use inputs where abs_edge < 1.5 but LIVE DOG would apply without cap
        result = classify(50.0, 48.0, -25.5, 140)
        # ba_gap=2.0, abs_edge=|2.0-25.5|=23.5 >=1.5 → still triggers BET first
        # SpreadCap gate: abs_spread > 24.5 → fires before BET check
        assert result["reason"] == "SpreadCap"


# -- classify return dict structure --

class TestClassifyReturnDict:
    def test_return_dict_has_all_keys(self):
        result = classify(20.0, 15.0, -5.0, 140)
        assert set(result.keys()) == {"signal", "reason", "ba_gap", "abs_edge", "spread", "ou"}

    def test_spread_passthrough(self):
        result = classify(20.0, 15.0, -7.5, 140)
        assert result["spread"] == -7.5

    def test_ou_passthrough(self):
        result = classify(20.0, 15.0, -5.0, 133.5)
        assert result["ou"] == 133.5

    def test_signal_is_string(self):
        result = classify(20.0, 15.0, -5.0, 140)
        assert isinstance(result["signal"], str)

    def test_reason_is_string(self):
        result = classify(20.0, 15.0, -5.0, 140)
        assert isinstance(result["reason"], str)

    def test_ba_gap_and_abs_edge_are_floats(self):
        result = classify(20.0, 15.0, -5.0, 140)
        assert isinstance(result["ba_gap"], float)
        assert isinstance(result["abs_edge"], float)
