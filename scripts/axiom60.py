"""
AXIOM-60 — Quantitative Margin-Volatility Engine
Deterministic filter chain for spread-adjusted efficiency analysis.
"""

PRECISION = 4           # decimal places for computed metric output
TEMPO_CAP = 148.0       # safety gate for high-variance games
EDGE_MIN = 1.5          # minimum alpha required to trigger BET signal
CONFIDENCE_WEIGHT = 12.5
AUDIT_SEAL = "AXIOM_VERIFIED_2026"


def compute_metrics(
    fav_kp: float,
    dog_kp: float,
    fav_tv: float,
    dog_tv: float,
    spread: float,
) -> dict:
    """Compute BA_Gap and Abs_Edge from dual-source efficiency inputs."""
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
    Returns signal classification, strength index, and computed metrics.
    """
    metrics = compute_metrics(fav_kp, dog_kp, fav_tv, dog_tv, spread)
    ba_gap = metrics["ba_gap"]
    abs_edge = metrics["abs_edge"]
    abs_spread = abs(spread)

    # Gate 1: Tempo
    if ou > TEMPO_CAP:
        signal = "PASS"
        reason = "TEMPO_OVERFLOW"
    # Gate 2: BET
    elif abs_edge >= EDGE_MIN:
        signal = "BET"
        reason = "Edge"
    # Gate 3: LIVE DOG
    elif abs_edge >= 1.0 and ba_gap < abs_spread:
        signal = "BET"
        reason = "LIVE_DOG"
    # Default
    else:
        signal = "PASS"
        reason = "Standard"

    # Strength Index (0–99.9) — non-zero only for BET signals
    if signal == "BET":
        strength = round(min(99.9, (abs_edge * CONFIDENCE_WEIGHT) + (TEMPO_CAP - ou)), 1)
    else:
        strength = 0

    return {
        "signal": signal,
        "strength": strength,
        "reason": reason,
        "ba_gap": ba_gap,
        "abs_edge": abs_edge,
        "spread": spread,
        "ou": ou,
        "audit_seal": AUDIT_SEAL,
    }
