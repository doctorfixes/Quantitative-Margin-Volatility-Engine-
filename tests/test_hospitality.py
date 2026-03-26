"""
Hospitality Mode — Unit Tests
Covers enabled/disabled toggle, all signal and reason mappings, and
ensures the original classification dict is never mutated.
"""
from scripts.hospitality import apply


# -- Enabled (default) --

class TestHospitalityEnabled:
    def test_bet_signal_mapped_to_priority(self):
        raw = {"signal": "BET", "reason": "Edge", "ba_gap": 2.0, "abs_edge": 1.5}
        result = apply(raw)
        assert result["signal"] == "PRIORITY"

    def test_pass_signal_mapped_to_standard(self):
        raw = {"signal": "PASS", "reason": "Standard", "ba_gap": 0.0, "abs_edge": 0.0}
        result = apply(raw)
        assert result["signal"] == "STANDARD"

    def test_edge_reason_mapped_to_alpha(self):
        raw = {"signal": "BET", "reason": "Edge"}
        assert apply(raw)["reason"] == "ALPHA"

    def test_live_dog_reason_mapped_to_secondary(self):
        raw = {"signal": "BET", "reason": "LIVE DOG"}
        assert apply(raw)["reason"] == "SECONDARY"

    def test_tempo_reason_mapped(self):
        raw = {"signal": "PASS", "reason": "Tempo"}
        assert apply(raw)["reason"] == "TEMPO"

    def test_spreadcap_reason_mapped(self):
        raw = {"signal": "PASS", "reason": "SpreadCap"}
        assert apply(raw)["reason"] == "RANGE"

    def test_standard_reason_mapped_to_default(self):
        raw = {"signal": "PASS", "reason": "Standard"}
        assert apply(raw)["reason"] == "DEFAULT"

    def test_numeric_fields_preserved(self):
        raw = {"signal": "BET", "reason": "Edge", "ba_gap": 3.5, "abs_edge": 2.0,
               "spread": -8.0, "ou": 140}
        result = apply(raw)
        assert result["ba_gap"] == 3.5
        assert result["abs_edge"] == 2.0
        assert result["spread"] == -8.0
        assert result["ou"] == 140

    def test_original_dict_not_mutated(self):
        raw = {"signal": "BET", "reason": "Edge"}
        apply(raw)
        assert raw["signal"] == "BET"
        assert raw["reason"] == "Edge"

    def test_returns_copy(self):
        raw = {"signal": "BET", "reason": "Edge"}
        result = apply(raw)
        result["signal"] = "MUTATED"
        assert raw["signal"] == "BET"

    def test_unknown_signal_passed_through(self):
        raw = {"signal": "UNKNOWN", "reason": "Edge"}
        result = apply(raw)
        assert result["signal"] == "UNKNOWN"


# -- Disabled --

class TestHospitalityDisabled:
    def test_disabled_preserves_bet_label(self):
        raw = {"signal": "BET", "reason": "Edge"}
        result = apply(raw, enabled=False)
        assert result["signal"] == "BET"

    def test_disabled_preserves_reason(self):
        raw = {"signal": "PASS", "reason": "Tempo"}
        result = apply(raw, enabled=False)
        assert result["reason"] == "Tempo"

    def test_disabled_returns_copy(self):
        raw = {"signal": "PASS", "reason": "Standard"}
        result = apply(raw, enabled=False)
        result["signal"] = "MUTATED"
        assert raw["signal"] == "PASS"
