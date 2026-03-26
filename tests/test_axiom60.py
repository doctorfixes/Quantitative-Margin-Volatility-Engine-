"""
AXIOM-60 Filter Chain — Validation Tests
Covers every gate + boundary edge cases.
"""
from scripts.axiom60 import classify, compute_metrics, AUDIT_SEAL


# -- Metric computation --

class TestMetrics:
    def test_ba_gap_calculation(self):
        # ba_gap = ((22-12) + (20-10)) / 2 = 10.0
        result = compute_metrics(22.0, 12.0, 20.0, 10.0, -8.0)
        assert result["ba_gap"] == 10.0

    def test_abs_edge_calculation(self):
        # abs_edge = |10.0 - 8.0| = 2.0
        result = compute_metrics(22.0, 12.0, 20.0, 10.0, -8.0)
        assert result["abs_edge"] == 2.0

    def test_zero_gap(self):
        result = compute_metrics(15.0, 15.0, 15.0, 15.0, -5.0)
        assert result["ba_gap"] == 0.0
        assert result["abs_edge"] == 5.0

    def test_ba_gap_averages_two_sources(self):
        """BA_Gap is the mean of two efficiency differentials."""
        # kp_diff=10, tv_diff=6 → ba_gap=8.0
        result = compute_metrics(20.0, 10.0, 16.0, 10.0, -5.0)
        assert result["ba_gap"] == 8.0


# -- Gate 1: Tempo filter --

class TestTempoGate:
    def test_ou_above_148_is_tempo_pass(self):
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 152)
        assert result["signal"] == "PASS"
        assert result["reason"] == "TEMPO_OVERFLOW"

    def test_ou_exactly_148_does_not_trigger(self):
        """O/U must be strictly > 148"""
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 148)
        assert result["reason"] != "TEMPO_OVERFLOW"

    def test_ou_148_point_1_triggers(self):
        result = classify(25.0, 15.0, 25.0, 15.0, -8.0, 148.1)
        assert result["reason"] == "TEMPO_OVERFLOW"


# -- Gate 2: BET --

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


# -- Gate 3: LIVE DOG --

class TestLiveDogGate:
    def test_live_dog_triggers(self):
        result = classify(18.0, 14.0, 18.0, 14.0, -5.0, 135)
        # ba_gap=4.0, abs_edge=|4.0-5.0|=1.0, ba_gap(4) < |spread|(5)
        assert result["signal"] == "BET"
        assert result["reason"] == "LIVE_DOG"

    def test_abs_edge_1_0_but_not_dog_aligned(self):
        """abs_edge >= 1.0 but ba_gap >= |spread| → no LIVE_DOG"""
        result = classify(22.0, 16.0, 22.0, 16.0, -5.0, 140)
        # ba_gap=6.0, abs_edge=|6.0-5.0|=1.0, ba_gap(6) >= |spread|(5)
        assert result["reason"] != "LIVE_DOG"

    def test_abs_edge_below_1_0_no_live_dog(self):
        result = classify(18.0, 14.5, 18.0, 14.5, -4.0, 140)
        # ba_gap=3.5, abs_edge=|3.5-4.0|=0.5
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"


# -- Default: Standard PASS --

class TestStandardPass:
    def test_no_edge_is_pass(self):
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        # ba_gap=3.0, abs_edge=|3.0-3.0|=0.0
        assert result["signal"] == "PASS"
        assert result["reason"] == "Standard"


# -- Strength Index --

class TestStrength:
    def test_bet_signal_has_positive_strength(self):
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        # abs_edge=2.0, strength = min(99.9, 2.0*12.5 + (148-138)) = 35.0
        assert result["strength"] == 35.0

    def test_pass_signal_has_zero_strength(self):
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        assert result["strength"] == 0

    def test_strength_capped_at_99_9(self):
        # Force a very large edge with low ou
        result = classify(50.0, 10.0, 50.0, 10.0, -5.0, 100)
        # ba_gap=40, abs_edge=|40-5|=35, strength = min(99.9, 35*12.5+48) = 99.9
        assert result["strength"] == 99.9

    def test_live_dog_strength_is_nonzero(self):
        result = classify(18.0, 14.0, 18.0, 14.0, -5.0, 135)
        assert result["strength"] > 0


# -- Audit Seal --

class TestAuditSeal:
    def test_audit_seal_present(self):
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["audit_seal"] == AUDIT_SEAL

    def test_audit_seal_value(self):
        assert AUDIT_SEAL == "AXIOM_VERIFIED_2026"


# -- Gate priority (Tempo overrides everything) --

class TestGatePriority:
    def test_tempo_overrides_bet_edge(self):
        """Even with abs_edge >= 1.5, Tempo fires first"""
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 155)
        assert result["reason"] == "TEMPO_OVERFLOW"
