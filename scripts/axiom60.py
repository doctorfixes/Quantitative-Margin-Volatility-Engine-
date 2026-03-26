"""
AXIOM HOOPS EDGE — 2026 Tournament Quant Engine
Deterministic filter chain for spread-adjusted efficiency analysis.
Includes AXIOM-60 Logic (Alpha Edge Detection) and Base44 AuditVault synchronization.
"""

AXIOM_CONFIG = {
    "TEMPO_CAP": 148.0,        # Safety Gate for High-Variance games
    "EDGE_MIN": 1.5,           # Minimum Alpha required to trigger BET signal
    "CONFIDENCE_WEIGHT": 12.5,
    "AUDIT_SEAL": "AXIOM_VERIFIED_2026",
}

PRECISION = 4  # decimal places for computed metric output


def compute_metrics(
    fav_kp: float, dog_kp: float, fav_tv: float, dog_tv: float, spread: float
) -> dict:
    """Compute BA_Gap (average KenPom + TeamRankings efficiency gap) and Abs_Edge."""
    ba_gap = ((fav_kp - dog_kp) + (fav_tv - dog_tv)) / 2
    abs_edge = abs(ba_gap - abs(spread))
    return {
        "ba_gap": round(ba_gap, PRECISION),
        "abs_edge": round(abs_edge, PRECISION),
    }


def classify(
    fav_kp: float, dog_kp: float, fav_tv: float, dog_tv: float, spread: float, ou: float
) -> dict:
    """
    Run the AXIOM-60 filter chain against a single entry.
    Returns signal classification, strength index, and computed metrics.
    """
    metrics = compute_metrics(fav_kp, dog_kp, fav_tv, dog_tv, spread)
    ba_gap = metrics["ba_gap"]
    abs_edge = metrics["abs_edge"]
    abs_spread = abs(spread)

    signal = "PASS"
    reason = None

    # Gate 1: Tempo
    if ou > AXIOM_CONFIG["TEMPO_CAP"]:
        reason = "TEMPO_OVERFLOW"
    # Gate 2: BET
    elif abs_edge >= AXIOM_CONFIG["EDGE_MIN"]:
        signal = "BET"
    # Gate 3: LIVE DOG
    elif abs_edge >= 1.0 and ba_gap < abs_spread:
        signal = "LIVE_DOG"

    # Strength Index (0–99.9) — non-zero only for BET signals
    strength = (
        min(99.9, (abs_edge * AXIOM_CONFIG["CONFIDENCE_WEIGHT"]) + (AXIOM_CONFIG["TEMPO_CAP"] - ou))
        if signal == "BET"
        else 0.0
    )

    return {
        "signal": signal,
        "strength": round(strength, 1),
        "reason": reason,
        "ba_gap": ba_gap,
        "abs_edge": abs_edge,
        "spread": spread,
        "ou": ou,
        "audit_seal": AXIOM_CONFIG["AUDIT_SEAL"],
    }
