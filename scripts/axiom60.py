"""
AXIOM-60 — Quantitative Margin-Volatility Engine
Deterministic filter chain for spread-adjusted efficiency analysis.
"""

from typing import Optional

PRECISION = 4  # decimal places for computed metric output
REGIME_DECAY = 0.97  # 0.97x decay factor applied to AdjEM in tournament regime

_ticker_memory: dict = {}


def apply_regime_decay(adj_em: float) -> float:
    """Apply 0.97x regime decay to an AdjEM value for tournament context."""
    return adj_em * REGIME_DECAY


def register_ticker(ticker: str, result: dict) -> None:
    """Register a classify result in ticker memory."""
    _ticker_memory[ticker] = result


def cleanup_tickers() -> int:
    """Clear all entries from ticker memory. Returns count of removed entries."""
    count = len(_ticker_memory)
    _ticker_memory.clear()
    return count


def compute_metrics(
    fav_adj_em: Optional[float], dog_adj_em: Optional[float], spread: float
) -> dict:
    """Compute BA_Gap and Abs_Edge from raw inputs.

    Returns None metrics when either AdjEM value is None.
    """
    if fav_adj_em is None or dog_adj_em is None:
        return {"ba_gap": None, "abs_edge": None}
    ba_gap = fav_adj_em - dog_adj_em
    abs_edge = abs(ba_gap - abs(spread))
    return {
        "ba_gap": round(ba_gap, PRECISION),
        "abs_edge": round(abs_edge, PRECISION),
    }


def classify(
    fav_adj_em: Optional[float],
    dog_adj_em: Optional[float],
    spread: float,
    ou: float,
    tournament_regime: bool = False,
) -> dict:
    """
    Run the AXIOM-60 filter chain against a single entry.
    Returns signal classification and computed metrics.

    When tournament_regime is True, AdjEM values are scaled by REGIME_DECAY (0.97x)
    before metric computation.  If either AdjEM value is None, the entry is
    classified as PASS with reason "NullAdjEM".
    """
    if fav_adj_em is None or dog_adj_em is None:
        return {
            "signal": "PASS",
            "reason": "NullAdjEM",
            "ba_gap": None,
            "abs_edge": None,
            "spread": spread,
            "ou": ou,
        }

    if tournament_regime:
        fav_adj_em = apply_regime_decay(fav_adj_em)
        dog_adj_em = apply_regime_decay(dog_adj_em)

    metrics = compute_metrics(fav_adj_em, dog_adj_em, spread)
    ba_gap = metrics["ba_gap"]
    abs_edge = metrics["abs_edge"]
    abs_spread = abs(spread)

    # Gate 1: Tempo
    if ou > 148:
        signal = "PASS"
        reason = "Tempo"
    # Gate 2: SpreadCap
    elif abs_spread > 24.5:
        signal = "PASS"
        reason = "SpreadCap"
    # Gate 3: BET
    elif abs_edge >= 1.5:
        signal = "BET"
        reason = "Edge"
    # Gate 4: LIVE DOG
    elif abs_edge >= 1.0 and ba_gap < abs_spread:
        signal = "BET"
        reason = "LIVE DOG"
    # Gate 5: Default
    else:
        signal = "PASS"
        reason = "Standard"

    return {
        "signal": signal,
        "reason": reason,
        "ba_gap": ba_gap,
        "abs_edge": abs_edge,
        "spread": spread,
        "ou": ou,
    }
