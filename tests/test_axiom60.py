"""
AXIOM HOOPS EDGE — 2026 Tournament Quant Engine
Filter Chain Validation Tests — covers every gate + boundary edge cases.
"""
from scripts.axiom60 import classify, compute_metrics, AXIOM_CONFIG


# -- AXIOM_CONFIG --

class TestAxiomConfig:
    def test_tempo_cap(self):
        assert AXIOM_CONFIG["TEMPO_CAP"] == 148.0

    def test_edge_min(self):
        assert AXIOM_CONFIG["EDGE_MIN"] == 1.5

    def test_confidence_weight(self):
        assert AXIOM_CONFIG["CONFIDENCE_WEIGHT"] == 12.5

    def test_audit_seal(self):
        assert AXIOM_CONFIG["AUDIT_SEAL"] == "AXIOM_VERIFIED_2026"


# -- Metric computation --

class TestMetrics:
    def test_ba_gap_calculation(self):
        # ((17-7) + (23-13)) / 2 = 10.0
        result = compute_metrics(17.0, 7.0, 23.0, 13.0, -8.0)
        assert result["ba_gap"] == 10.0

    def test_abs_edge_calculation(self):
        # ba_gap=10.0, abs_edge=|10.0-8.0|=2.0
        result = compute_metrics(17.0, 7.0, 23.0, 13.0, -8.0)
        assert result["abs_edge"] == 2.0

    def test_zero_gap(self):
        result = compute_metrics(15.0, 15.0, 15.0, 15.0, -5.0)
        assert result["ba_gap"] == 0.0
        assert result["abs_edge"] == 5.0

    def test_averaging_two_sources(self):
        """BA_Gap is the average of KenPom and TeamRankings gaps."""
        # KP gap = 12, TV gap = 8 → average = 10
        result = compute_metrics(20.0, 8.0, 18.0, 10.0, -5.0)
        assert result["ba_gap"] == 10.0


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

    def test_abs_edge_exactly_1_5_triggers(self):
        """Threshold is >= 1.5"""
        # ba_gap=6.5, abs_edge=|6.5-5.0|=1.5
        result = classify(20.0, 13.5, 20.0, 13.5, -5.0, 140)
        assert result["signal"] == "BET"

    def test_abs_edge_1_49_does_not_trigger_bet(self):
        # ba_gap=5.49, abs_edge=|5.49-4.0|=1.49
        result = classify(20.0, 14.51, 20.0, 14.51, -4.0, 140)
        assert result["signal"] != "BET"

    def test_bet_has_no_reason(self):
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["reason"] is None


# -- Gate 3: LIVE DOG --

class TestLiveDogGate:
    def test_live_dog_triggers(self):
        # ba_gap=4.0, abs_edge=|4.0-5.0|=1.0, ba_gap(4) < |spread|(5)
        result = classify(18.0, 14.0, 18.0, 14.0, -5.0, 135)
        assert result["signal"] == "LIVE_DOG"

    def test_live_dog_has_no_reason(self):
        result = classify(18.0, 14.0, 18.0, 14.0, -5.0, 135)
        assert result["reason"] is None

    def test_abs_edge_1_0_but_not_dog_aligned(self):
        """abs_edge >= 1.0 but ba_gap >= |spread| → no LIVE_DOG"""
        # ba_gap=6.0, abs_edge=|6.0-5.0|=1.0, ba_gap(6) >= |spread|(5)
        result = classify(22.0, 16.0, 22.0, 16.0, -5.0, 140)
        assert result["signal"] != "LIVE_DOG"

    def test_abs_edge_below_1_0_no_live_dog(self):
        # ba_gap=3.5, abs_edge=|3.5-4.0|=0.5
        result = classify(18.0, 14.5, 18.0, 14.5, -4.0, 140)
        assert result["signal"] == "PASS"
        assert result["reason"] is None


# -- Default PASS --

class TestStandardPass:
    def test_no_edge_is_pass(self):
        # ba_gap=3.0, abs_edge=|3.0-3.0|=0.0
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        assert result["signal"] == "PASS"
        assert result["reason"] is None


# -- Strength Index --

class TestStrengthIndex:
    def test_bet_has_positive_strength(self):
        # ba_gap=10.0, abs_edge=2.0
        # strength = min(99.9, (2.0 * 12.5) + (148.0 - 138)) = min(99.9, 25.0 + 10.0) = 35.0
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["strength"] == 35.0

    def test_pass_has_zero_strength(self):
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        assert result["strength"] == 0.0

    def test_live_dog_has_zero_strength(self):
        result = classify(18.0, 14.0, 18.0, 14.0, -5.0, 135)
        assert result["strength"] == 0.0

    def test_strength_capped_at_99_9(self):
        """Very large edge + low O/U should be capped at 99.9"""
        # ba_gap=40.0, abs_edge=35.0, strength = min(99.9, 35*12.5 + 48) = min(99.9, 485.5) = 99.9
        result = classify(50.0, 10.0, 50.0, 10.0, -5.0, 100)
        assert result["strength"] == 99.9


# -- Audit Seal --

class TestAuditSeal:
    def test_bet_carries_audit_seal(self):
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 138)
        assert result["audit_seal"] == "AXIOM_VERIFIED_2026"

    def test_pass_carries_audit_seal(self):
        result = classify(20.0, 17.0, 20.0, 17.0, -3.0, 140)
        assert result["audit_seal"] == "AXIOM_VERIFIED_2026"


# -- Gate priority (Tempo overrides everything) --

class TestGatePriority:
    def test_tempo_overrides_bet_edge(self):
        """Even with abs_edge >= 1.5, Tempo fires first"""
        result = classify(22.0, 12.0, 22.0, 12.0, -8.0, 155)
        assert result["reason"] == "TEMPO_OVERFLOW"
        assert result["signal"] == "PASS"
