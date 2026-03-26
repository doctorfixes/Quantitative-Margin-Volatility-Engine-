"""
SelectionDash — processes the live Sweet 16 slate through AXIOM-60.

Usage
-----
    from selection_dash import SelectionDash

    processed = SelectionDash()
    for game in processed:
        print(game["game_id"], game["result"]["signal"])
"""

from data.sweet16 import live_tournament_slate
from lib.axiom60 import run_axiom60


def SelectionDash() -> list:
    """
    Run AXIOM-60 against every game in the live tournament slate.

    Returns a list of game dicts, each augmented with a ``result`` key
    containing the AXIOM-60 signal output.
    """
    return [
        {**game, "result": run_axiom60(game)}
        for game in live_tournament_slate
    ]


if __name__ == "__main__":
    for entry in SelectionDash():
        res = entry["result"]
        print(
            f"{entry['game_id']:12s}  {entry['favorite']:18s} vs "
            f"{entry['underdog']:18s}  "
            f"signal={res['signal']:4s}  reason={res['reason']}"
        )
