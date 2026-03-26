"""
AXIOM-60 API — FastAPI server exposing the classification engine.

Start locally:
    uvicorn api.main:app --reload

Production (Railway):
    web: uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}

Authentication:
    Every request must include the header  X-API-Key: <AXIOM_API_KEY>.
"""

import os

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from scripts.axiom60 import classify

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=_API_KEY_NAME, auto_error=False)

_AXIOM_API_KEY = os.environ.get("AXIOM_API_KEY", "")
if not _AXIOM_API_KEY:
    raise RuntimeError(
        "AXIOM_API_KEY environment variable is not set. "
        "Set it before starting the server."
    )


def _require_key(api_key: str = Security(_api_key_header)) -> str:
    if api_key != _AXIOM_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return api_key


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AXIOM-60",
    description="Quantitative Margin-Volatility Engine — deterministic filter chain for spread-adjusted efficiency analysis.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MatchupIn(BaseModel):
    fav_adj_em: float
    dog_adj_em: float
    spread: float
    ou: float


class ClassifyOut(BaseModel):
    signal: str
    reason: str
    ba_gap: float
    abs_edge: float
    spread: float
    ou: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/healthz", include_in_schema=False)
def healthz():
    """Liveness probe — no auth required."""
    return {"status": "ok"}


@app.post(
    "/classify",
    response_model=ClassifyOut,
    summary="Classify a matchup",
    description=(
        "Run the AXIOM-60 five-gate filter chain against a single matchup entry. "
        "Returns the signal tier (BET / PASS) with the triggering reason and computed metrics."
    ),
    dependencies=[Depends(_require_key)],
)
def classify_matchup(body: MatchupIn) -> ClassifyOut:
    result = classify(body.fav_adj_em, body.dog_adj_em, body.spread, body.ou)
    return ClassifyOut(**result)
