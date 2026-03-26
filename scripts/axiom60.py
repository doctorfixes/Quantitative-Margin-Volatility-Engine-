"""
AXIOM-60 — Quantitative Margin-Volatility Engine
Deterministic filter chain for spread-adjusted efficiency analysis.
"""

PRECISION = 4  # decimal places for computed metric output


def compute_metrics(fav_adj_em: float, dog_adj_em: float, spread: float) -> dict:
    """Compute BA_Gap and Abs_Edge from raw inputs."""
    ba_gap = fav_adj_em - dog_adj_em
    abs_edge = abs(ba_gap - abs(spread))
    return {
        "ba_gap": round(ba_gap, PRECISION),
        "abs_edge": round(abs_edge, PRECISION),
    }


def classify(fav_adj_em: float, dog_adj_em: float, spread: float, ou: float) -> dict:
    """
    Run the AXIOM-60 filter chain against a single entry.
    Returns signal classification and computed metrics.
    """
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


def filter_active_slate(games: list) -> list:
    """
    Simplified view filter: return only games where signal is 'BET'
    or the game is marked as featured (is_featured=True).
    """
    return [g for g in games if g.get("signal") == "BET" or g.get("is_featured")]
