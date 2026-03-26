"""
2026 NCAA Tournament — Sweet 16 live slate.

Each entry carries the four AXIOM-60 inputs alongside contextual metadata:
  fav_adj_em  – favorite's adjusted efficiency margin (KenPom-style)
  dog_adj_em  – underdog's adjusted efficiency margin
  spread      – closing spread (negative = favorite lays that many points)
  ou          – closing over/under total
"""

live_tournament_slate = [
    # East Region
    {
        "game_id": "S16_E_1",
        "region": "East",
        "favorite": "Duke",
        "underdog": "Marquette",
        "fav_adj_em": 30.2,
        "dog_adj_em": 20.5,
        "spread": -8.5,
        "ou": 142.5,
    },
    {
        "game_id": "S16_E_2",
        "region": "East",
        "favorite": "Tennessee",
        "underdog": "Mississippi State",
        "fav_adj_em": 26.1,
        "dog_adj_em": 17.3,
        "spread": -9.0,
        "ou": 137.0,
    },
    # West Region
    {
        "game_id": "S16_W_1",
        "region": "West",
        "favorite": "Kansas",
        "underdog": "Utah State",
        "fav_adj_em": 27.8,
        "dog_adj_em": 18.6,
        "spread": -7.0,
        "ou": 139.5,
    },
    {
        "game_id": "S16_W_2",
        "region": "West",
        "favorite": "Gonzaga",
        "underdog": "Michigan",
        "fav_adj_em": 29.4,
        "dog_adj_em": 21.0,
        "spread": -6.5,
        "ou": 145.0,
    },
    # South Region
    {
        "game_id": "S16_S_1",
        "region": "South",
        "favorite": "Auburn",
        "underdog": "Illinois",
        "fav_adj_em": 28.9,
        "dog_adj_em": 22.4,
        "spread": -5.5,
        "ou": 141.0,
    },
    {
        "game_id": "S16_S_2",
        "region": "South",
        "favorite": "Houston",
        "underdog": "Creighton",
        "fav_adj_em": 25.7,
        "dog_adj_em": 19.1,
        "spread": -6.0,
        "ou": 136.5,
    },
    # Midwest Region
    {
        "game_id": "S16_MW_1",
        "region": "Midwest",
        "favorite": "Iowa State",
        "underdog": "UCLA",
        "fav_adj_em": 27.3,
        "dog_adj_em": 20.8,
        "spread": -5.0,
        "ou": 140.0,
    },
    {
        "game_id": "S16_MW_2",
        "region": "Midwest",
        "favorite": "Purdue",
        "underdog": "Saint Mary's",
        "fav_adj_em": 24.6,
        "dog_adj_em": 14.9,
        "spread": -11.5,
        "ou": 134.0,
    },
]
