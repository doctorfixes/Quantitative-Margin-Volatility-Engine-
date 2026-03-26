"""
AXIOM-60 REST API — Production
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from scripts.axiom60 import classify, compute_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("axiom60")


@asynccontextmanager
async def lifespan(application: FastAPI):
    if not os.environ.get("AXIOM_API_KEY"):
        logger.warning("AXIOM_API_KEY not set — all auth endpoints return 401.")
    yield


app = FastAPI(
    title="AXIOM-60 Volatility Engine",
    description="Deterministic five-gate filter chain for spread-adjusted efficiency analysis.",
    version="1.0",
    lifespan=lifespan,
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})


# CORS
_cors = os.environ.get("AXIOM_CORS_ORIGINS", "")
_origins = [o.strip() for o in _cors.split(",") if o.strip()] if _cors else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Auth
_KEY = os.environ.get("AXIOM_API_KEY", "")


def _verify_api_key(x_api_key: str):
    if not _KEY:
        raise HTTPException(status_code=401, detail="AXIOM_API_KEY not configured on server.")
    if x_api_key != _KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")


# Logging middleware
@app.middleware("http")
async def _log(request: Request, call_next):
    t = time.time()
    resp = await call_next(request)
    logger.info(
        "%s %s → %s (%.3fs)",
        request.method, request.url.path, resp.status_code, time.time() - t,
    )
    return resp


# Models
class MatchupIn(BaseModel):
    fav_adj_em: float = Field(..., description="Favorite AdjEM")
    dog_adj_em: float = Field(..., description="Underdog AdjEM")
    spread: float = Field(..., description="Spread")
    ou: float = Field(..., description="O/U total")


class MetricsIn(BaseModel):
    fav_adj_em: float
    dog_adj_em: float
    spread: float


class Result(BaseModel):
    signal: str
    reason: str
    ba_gap: float
    abs_edge: float
    spread: float
    ou: float


class BatchIn(BaseModel):
    matchups: List[MatchupIn] = Field(..., min_length=1, max_length=100)


class BatchOut(BaseModel):
    results: List[Result]
    summary: dict


# Endpoints

@app.get("/health", tags=["status"])
def health():
    return {"status": "ok", "engine": "AXIOM-60"}


@app.post("/classify", response_model=Result, tags=["engine"])
@limiter.limit("60/minute")
def classify_matchup(request: Request, body: MatchupIn, x_api_key: str = Header("")):
    _verify_api_key(x_api_key)
    return classify(body.fav_adj_em, body.dog_adj_em, body.spread, body.ou)


@app.post("/classify/batch", response_model=BatchOut, tags=["engine"])
@limiter.limit("20/minute")
def classify_batch(request: Request, body: BatchIn, x_api_key: str = Header("")):
    _verify_api_key(x_api_key)
    results = [classify(m.fav_adj_em, m.dog_adj_em, m.spread, m.ou) for m in body.matchups]
    summary = {
        "total": len(results),
        "bet": sum(1 for r in results if r["signal"] == "BET" and r["reason"] == "Edge"),
        "live_dog": sum(1 for r in results if r["reason"] == "LIVE DOG"),
        "pass_tempo": sum(1 for r in results if r["reason"] == "Tempo"),
        "pass_spreadcap": sum(1 for r in results if r["reason"] == "SpreadCap"),
        "pass_standard": sum(1 for r in results if r["reason"] == "Standard"),
    }
    logger.info(
        "Batch: %d → %d BET, %d DOG, %d PASS",
        summary["total"], summary["bet"], summary["live_dog"],
        summary["pass_tempo"] + summary["pass_spreadcap"] + summary["pass_standard"],
    )
    return {"results": results, "summary": summary}


@app.post("/metrics", tags=["engine"])
@limiter.limit("60/minute")
def metrics(request: Request, body: MetricsIn, x_api_key: str = Header("")):
    _verify_api_key(x_api_key)
    return compute_metrics(body.fav_adj_em, body.dog_adj_em, body.spread)
