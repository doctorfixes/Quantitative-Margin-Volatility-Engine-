"""
api/main.py — FastAPI application that bridges the AXIOM-60 engine to Base44.

Base44 app : Axiom-60  (https://app.base44.com/apps/69c3204219e8e63b63a9e14e/editor)
Base44 (https://base44.com) calls this service as an external integration via
its auto-generated REST connector.  Every endpoint returns JSON that Base44's
SDK can consume directly.

When the ``BASE44_API_KEY`` environment variable is set, classification results
are automatically pushed to the Matchup entity inside the Base44 app.

Start locally:
    uvicorn api.main:app --reload --port 8000
"""

import logging
import os
from typing import List, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from api.base44_client import Base44AuthError, Base44Client
from scripts.axiom60 import classify, compute_metrics

logger = logging.getLogger(__name__)


def _get_base44_client() -> Optional[Base44Client]:
    """Return a Base44Client when BASE44_API_KEY is set, else None."""
    if os.environ.get("BASE44_API_KEY"):
        try:
            return Base44Client.from_env()
        except Base44AuthError:
            pass
    return None


app = FastAPI(
    title="AXIOM-60 API",
    description=(
        "Quantitative Margin-Volatility Engine — deterministic filter chain "
        "for spread-adjusted efficiency analysis.  Designed as a Base44 "
        "external integration."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class MatchupRequest(BaseModel):
    fav_adj_em: float = Field(..., description="Favorite adjusted efficiency margin")
    dog_adj_em: float = Field(..., description="Underdog adjusted efficiency margin")
    spread: float = Field(..., description="Posted spread (negative favors favorite)")
    ou: float = Field(..., description="Over/under total")


class MetricsResponse(BaseModel):
    ba_gap: float = Field(..., description="FavAdjEM - DogAdjEM")
    abs_edge: float = Field(..., description="|BA_Gap - |Spread||")


class ClassifyResponse(BaseModel):
    signal: str = Field(..., description="BET or PASS")
    reason: str = Field(..., description="Filter gate that fired: Edge, LIVE DOG, Tempo, SpreadCap, Standard")
    ba_gap: float
    abs_edge: float
    spread: float
    ou: float


class BatchRequest(BaseModel):
    entries: List[MatchupRequest] = Field(..., min_length=1, description="One or more matchups to classify")


class BatchResponse(BaseModel):
    results: List[ClassifyResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", summary="Liveness probe")
def health() -> dict:
    """Returns 200 OK when the service is running.  Used by Base44 to verify
    that the integration endpoint is reachable before wiring it into an app."""
    return {"status": "ok", "engine": "AXIOM-60"}


@app.post("/metrics", response_model=MetricsResponse, summary="Compute raw metrics")
def metrics(req: MatchupRequest) -> MetricsResponse:
    """Compute BA_Gap and Abs_Edge without running the full filter chain."""
    result = compute_metrics(req.fav_adj_em, req.dog_adj_em, req.spread)
    return MetricsResponse(**result)


@app.post("/classify", response_model=ClassifyResponse, summary="Classify a single matchup")
def classify_single(req: MatchupRequest) -> ClassifyResponse:
    """Run the AXIOM-60 five-gate filter chain against one matchup and return
    the signal classification.  This is the primary endpoint consumed by a
    Base44 app's backend function or automation trigger.

    When ``BASE44_API_KEY`` is set the result is also written to the Matchup
    entity inside the Base44 Axiom-60 app.
    """
    result = classify(req.fav_adj_em, req.dog_adj_em, req.spread, req.ou)
    response = ClassifyResponse(**result)
    client = _get_base44_client()
    if client is not None:
        try:
            client.create_matchup(response.model_dump())
        except (httpx.HTTPError, Base44AuthError) as exc:
            logger.warning("Base44 push failed: %s", exc)
    return response


@app.post("/classify/batch", response_model=BatchResponse, summary="Classify multiple matchups")
def classify_batch(req: BatchRequest) -> BatchResponse:
    """Run the filter chain across a list of matchups in a single request.
    Useful for seeding a Base44 data entity with a full slate of games.

    When ``BASE44_API_KEY`` is set every result is also written to the Matchup
    entity inside the Base44 Axiom-60 app.
    """
    results = [
        ClassifyResponse(**classify(e.fav_adj_em, e.dog_adj_em, e.spread, e.ou))
        for e in req.entries
    ]
    client = _get_base44_client()
    if client is not None:
        for row in results:
            try:
                client.create_matchup(row.model_dump())
            except (httpx.HTTPError, Base44AuthError) as exc:
                logger.warning("Base44 push failed: %s", exc)
    return BatchResponse(results=results)
