"""
AXIOM-60 — Quantitative Margin-Volatility Engine
Deterministic filter chain for spread-adjusted efficiency analysis.

Patch 2.6.1 — Sweet 16 Hardening:
  - Regime decay (0.97) applied to O/U before tempo gate
  - Dual efficiency sources (KP + TV) averaged for BA_Gap
  - Strength score added to BET outputs
"""

PRECISION = 4  # decimal places for computed metric output
REGIME_DECAY = 0.97  # Sweet 16 Tempo Adjustment


def compute_metrics(
    fav_kp: float,
    dog_kp: float,
    fav_tv: float,
    dog_tv: float,
    spread: float,
) -> dict:
    """Compute BA_Gap and Abs_Edge from dual efficiency sources (KP + TV averaged)."""
    ba_gap = ((fav_kp - dog_kp) + (fav_tv - dog_tv)) / 2
    abs_edge = abs(ba_gap - abs(spread))
    return {
        "ba_gap": round(ba_gap, PRECISION),
        "abs_edge": round(abs_edge, PRECISION),
    }


def classify(
    fav_kp: float,
    dog_kp: float,
    fav_tv: float,
    dog_tv: float,
    spread: float,
    ou: float,
) -> dict:
    """
    Run the AXIOM-60 filter chain against a single entry.
    Returns signal classification, computed metrics, adj_ou, and strength.

    Patch 2.6.1: O/U is scaled by REGIME_DECAY (0.97) before gate evaluation.
    Strength is non-zero only for BET signals.
    """
    adj_ou = ou * REGIME_DECAY  # Sweet 16 Tempo Adjustment
    metrics = compute_metrics(fav_kp, dog_kp, fav_tv, dog_tv, spread)
    ba_gap = metrics["ba_gap"]
    abs_edge = metrics["abs_edge"]
    abs_spread = abs(spread)

    # Gate 1: Tempo
    if adj_ou > 148:
        signal = "PASS"
        reason = "Tempo"
        strength = 0
    # Gate 2: SpreadCap
    elif abs_spread > 24.5:
        signal = "PASS"
        reason = "SpreadCap"
        strength = 0
    # Gate 3: BET
    elif abs_edge >= 1.5:
        signal = "BET"
        reason = "Edge"
        strength = min(99.9, (abs_edge * 12.5) + (148 - adj_ou))
    # Gate 4: LIVE DOG
    elif abs_edge >= 1.0 and ba_gap < abs_spread:
        signal = "BET"
        reason = "LIVE DOG"
        strength = min(99.9, (abs_edge * 12.5) + (148 - adj_ou))
    # Gate 5: Default
    else:
        signal = "PASS"
        reason = "Standard"
        strength = 0

    return {
        "signal": signal,
        "reason": reason,
        "ba_gap": ba_gap,
        "abs_edge": abs_edge,
        "spread": spread,
        "ou": ou,
        "adj_ou": round(adj_ou, PRECISION),
        "strength": round(strength, PRECISION),
    }
