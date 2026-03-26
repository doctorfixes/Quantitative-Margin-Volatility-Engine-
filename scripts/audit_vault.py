"""
Audit Vault — Automated Win/Loss Ledger

Records AXIOM-60 predictions and actual outcomes to maintain a transparent,
verifiable performance ledger.  All BET signal results are tracked; PASS
signals are stored for completeness but excluded from the win/loss tally.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

Outcome = Literal["WIN", "LOSS", "PUSH", "PENDING"]


class AuditVault:
    """In-memory ledger of AXIOM-60 predictions and their outcomes."""

    def __init__(self) -> None:
        self._records: list[dict] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def record(
        self,
        classification: dict,
        *,
        game_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Store a new prediction and return its unique record ID.

        Only BET signals count toward the win/loss tally; PASS signals are
        recorded with outcome ``"PENDING"`` so the full history is auditable.
        """
        record_id = str(uuid.uuid4())
        entry = {
            "id": record_id,
            "game_id": game_id,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "signal": classification["signal"],
            "reason": classification["reason"],
            "ba_gap": classification.get("ba_gap"),
            "abs_edge": classification.get("abs_edge"),
            "spread": classification.get("spread"),
            "ou": classification.get("ou"),
            "outcome": "PENDING",
        }
        self._records.append(entry)
        return record_id

    def settle(self, record_id: str, outcome: Outcome) -> None:
        """Attach a final outcome to an existing record by its ID."""
        for entry in self._records:
            if entry["id"] == record_id:
                entry["outcome"] = outcome
                return
        raise KeyError(f"No record found with id={record_id!r}")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """
        Return aggregate win/loss statistics for all BET signals.

        Only WIN and LOSS outcomes count toward the denominator; PENDING and
        PUSH records are excluded from the win-percentage calculation.
        """
        bets = [r for r in self._records if r["signal"] == "BET"]
        wins = sum(1 for r in bets if r["outcome"] == "WIN")
        losses = sum(1 for r in bets if r["outcome"] == "LOSS")
        settled = wins + losses
        win_pct = round(wins / settled, 4) if settled else None
        return {
            "total_bets": len(bets),
            "wins": wins,
            "losses": losses,
            "win_pct": win_pct,
        }

    def records(self) -> list[dict]:
        """Return a shallow copy of all stored records."""
        return [dict(r) for r in self._records]
