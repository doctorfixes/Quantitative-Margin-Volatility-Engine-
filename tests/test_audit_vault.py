"""
Audit Vault — Unit Tests
Covers record creation, outcome settlement, summary statistics, and
the 13-1 transparency record referenced in the project specification.
"""
import pytest
from scripts.audit_vault import AuditVault

SAMPLE_BET = {
    "signal": "BET", "reason": "Edge",
    "ba_gap": 2.0, "abs_edge": 1.5, "spread": -8.0, "ou": 140,
}
SAMPLE_PASS = {
    "signal": "PASS", "reason": "Standard",
    "ba_gap": 0.5, "abs_edge": 0.5, "spread": -5.0, "ou": 138,
}


# -- Record creation --

class TestRecord:
    def test_returns_string_id(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        assert isinstance(rid, str) and len(rid) > 0

    def test_initial_outcome_is_pending(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["outcome"] == "PENDING"

    def test_signal_stored_correctly(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["signal"] == "BET"

    def test_reason_stored_correctly(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["reason"] == "Edge"

    def test_metrics_stored(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["ba_gap"] == 2.0
        assert entry["abs_edge"] == 1.5

    def test_game_id_optional(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET, game_id="DUKE-UNC-2025")
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["game_id"] == "DUKE-UNC-2025"

    def test_custom_timestamp_stored(self):
        vault = AuditVault()
        ts = "2025-03-15T20:00:00+00:00"
        rid = vault.record(SAMPLE_BET, timestamp=ts)
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["timestamp"] == ts

    def test_records_returns_copies(self):
        vault = AuditVault()
        vault.record(SAMPLE_BET)
        copies = vault.records()
        copies[0]["signal"] = "MUTATED"
        assert vault.records()[0]["signal"] == "BET"


# -- Settlement --

class TestSettle:
    def test_settle_win(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        vault.settle(rid, "WIN")
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["outcome"] == "WIN"

    def test_settle_loss(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        vault.settle(rid, "LOSS")
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["outcome"] == "LOSS"

    def test_settle_push(self):
        vault = AuditVault()
        rid = vault.record(SAMPLE_BET)
        vault.settle(rid, "PUSH")
        entry = next(r for r in vault.records() if r["id"] == rid)
        assert entry["outcome"] == "PUSH"

    def test_settle_unknown_id_raises_key_error(self):
        vault = AuditVault()
        with pytest.raises(KeyError):
            vault.settle("nonexistent-id", "WIN")


# -- Summary statistics --

class TestSummary:
    def test_empty_vault(self):
        vault = AuditVault()
        s = vault.summary()
        assert s["total_bets"] == 0
        assert s["wins"] == 0
        assert s["losses"] == 0
        assert s["win_pct"] is None

    def test_13_1_record(self):
        """Audit Vault must reproduce the 13-1 transparency record."""
        vault = AuditVault()
        ids = [vault.record(SAMPLE_BET) for _ in range(14)]
        for rid in ids[:13]:
            vault.settle(rid, "WIN")
        vault.settle(ids[13], "LOSS")
        s = vault.summary()
        assert s["wins"] == 13
        assert s["losses"] == 1
        assert s["win_pct"] == round(13 / 14, 4)

    def test_pass_signals_excluded_from_tally(self):
        vault = AuditVault()
        vault.record(SAMPLE_PASS)
        s = vault.summary()
        assert s["total_bets"] == 0

    def test_pending_excluded_from_win_pct(self):
        vault = AuditVault()
        rid1 = vault.record(SAMPLE_BET)
        vault.record(SAMPLE_BET)  # stays PENDING
        vault.settle(rid1, "WIN")
        s = vault.summary()
        assert s["wins"] == 1
        assert s["losses"] == 0
        assert s["win_pct"] == 1.0

    def test_push_excluded_from_win_pct_denominator(self):
        vault = AuditVault()
        rid1 = vault.record(SAMPLE_BET)
        rid2 = vault.record(SAMPLE_BET)
        vault.settle(rid1, "WIN")
        vault.settle(rid2, "PUSH")
        s = vault.summary()
        assert s["wins"] == 1
        assert s["losses"] == 0
        assert s["win_pct"] == 1.0

    def test_multiple_bets_tallied(self):
        vault = AuditVault()
        r1 = vault.record(SAMPLE_BET)
        r2 = vault.record(SAMPLE_BET)
        r3 = vault.record(SAMPLE_BET)
        vault.settle(r1, "WIN")
        vault.settle(r2, "WIN")
        vault.settle(r3, "LOSS")
        s = vault.summary()
        assert s["total_bets"] == 3
        assert s["wins"] == 2
        assert s["losses"] == 1
        assert s["win_pct"] == round(2 / 3, 4)
