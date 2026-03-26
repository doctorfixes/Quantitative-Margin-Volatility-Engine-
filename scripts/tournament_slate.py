"""
Live Tournament Slate — Sweet 16 matchup data for AXIOM-60 processing.
Each entry contains team names, spread, O/U, KenPom ratings (KP),
and tempo-adjusted efficiency values (TV) used as fav_adj_em / dog_adj_em.
"""

from scripts.axiom60 import classify

LIVE_TOURNAMENT_SLATE = [
    {
        "id": "S16_01",
        "fav": "Purdue",
        "dog": "Texas",
        "spread": -7.5,
        "ou": 147.5,
        "favKP": 30.2,
        "dogKP": 21.4,
        "favTV": 31.5,
        "dogTV": 22.8,
    },
    {
        "id": "S16_02",
        "fav": "Nebraska",
        "dog": "Iowa",
        "spread": -1.5,
        "ou": 131.5,
        "favKP": 18.5,
        "dogKP": 16.2,
        "favTV": 19.4,
        "dogTV": 16.9,
    },
    {
        "id": "S16_03",
        "fav": "Houston",
        "dog": "Illinois",
        "spread": -2.5,
        "ou": 139.5,
        "favKP": 32.1,
        "dogKP": 24.5,
        "favTV": 33.4,
        "dogTV": 25.1,
    },
    {
        "id": "S16_04",
        "fav": "Arizona",
        "dog": "Arkansas",
        "spread": -8.5,
        "ou": 164.5,
        "favKP": 27.2,
        "dogKP": 20.8,
        "favTV": 28.5,
        "dogTV": 21.4,
    },
]


def run_slate(slate=None):
    """
    Run every entry in the slate through the AXIOM-60 filter chain.

    Uses favTV / dogTV as the tempo-adjusted efficiency margins
    (fav_adj_em / dog_adj_em).  Returns a list of result dicts, each
    containing the original matchup fields merged with the engine output.
    """
    if slate is None:
        slate = LIVE_TOURNAMENT_SLATE
    results = []
    for game in slate:
        engine_out = classify(
            fav_adj_em=game["favTV"],
            dog_adj_em=game["dogTV"],
            spread=game["spread"],
            ou=game["ou"],
        )
        results.append({**game, **engine_out})
    return results
