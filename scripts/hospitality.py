"""
Hospitality Mode — Stealth Logic Overlay

Translates raw AXIOM-60 signal classifications into neutral display labels
suitable for professional environments where sports-betting vocabulary is
inappropriate (e.g., broadcast suites, corporate dashboards).

When enabled, the overlay replaces BET/PASS signals and their reasons with
innocuous-sounding equivalents.  All numeric metrics are preserved unchanged.
"""

# Signal → neutral label
_SIGNAL_MAP: dict[str, str] = {
    "BET": "PRIORITY",
    "PASS": "STANDARD",
}

# Reason → neutral label
_REASON_MAP: dict[str, str] = {
    "Edge": "ALPHA",
    "LIVE DOG": "SECONDARY",
    "Tempo": "TEMPO",
    "SpreadCap": "RANGE",
    "Standard": "DEFAULT",
}


def apply(classification: dict, *, enabled: bool = True) -> dict:
    """
    Return a copy of *classification* with hospitality-safe labels applied.

    When *enabled* is False the original result is returned unchanged so the
    full BET/PASS vocabulary is preserved for internal use.
    """
    if not enabled:
        return dict(classification)

    result = dict(classification)
    result["signal"] = _SIGNAL_MAP.get(classification["signal"], classification["signal"])
    result["reason"] = _REASON_MAP.get(classification["reason"], classification["reason"])
    return result
