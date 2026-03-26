"""
Base44 Client — Real-Time Score Ingestion

Thin wrapper around the Base44 REST API for the AXIOM-60 Matchup entity.
Uses only the Python standard library (no third-party HTTP packages required).

Authentication:  set the BASE44_API_KEY environment variable.
App ID:          69c3204219e8e63b63a9e14e
Entity:          Matchup
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

APP_ID = "69c3204219e8e63b63a9e14e"
BASE_URL = f"https://api.base44.com/apps/{APP_ID}/entities/Matchup"
_API_KEY_ENV = "BASE44_API_KEY"


class Base44Error(Exception):
    """Raised when the Base44 API returns an unexpected response."""


class Base44Client:
    """Minimal synchronous REST client for Base44 Matchup entities."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.environ.get(_API_KEY_ENV, "")
        if not self._api_key:
            raise Base44Error(
                f"No API key found. Set the {_API_KEY_ENV} environment variable."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, url: str, body: Optional[dict] = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urlopen(req) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            raise Base44Error(f"HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise Base44Error(f"Network error: {exc.reason}") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_matchups(self) -> list:
        """Return all Matchup entities from Base44."""
        result = self._request("GET", BASE_URL)
        if isinstance(result, list):
            return result
        return result.get("items", result.get("data", []))

    def get_matchup(self, matchup_id: str) -> dict:
        """Fetch a single Matchup entity by ID."""
        url = f"{BASE_URL}/{matchup_id}"
        return self._request("GET", url)

    def push_result(self, matchup_id: str, payload: dict) -> dict:
        """Update a Matchup entity with classification results."""
        url = f"{BASE_URL}/{matchup_id}"
        return self._request("PATCH", url, body=payload)
