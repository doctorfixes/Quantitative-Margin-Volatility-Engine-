"""
api/base44_client.py — Python client for the Base44 app "Axiom-60".

App ID  : 69c3204219e8e63b63a9e14e
App URL : https://app.base44.com/apps/69c3204219e8e63b63a9e14e/editor

Usage
-----
Set the environment variable BASE44_API_KEY to your Base44 API key, then:

    from api.base44_client import Base44Client
    client = Base44Client.from_env()
    client.create_matchup({"signal": "BET", "reason": "Edge", ...})

The Matchup entity in the Base44 app stores the classification output of a
single game entry processed by the AXIOM-60 filter chain.
"""

import os
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_ID = "69c3204219e8e63b63a9e14e"
BASE_URL = f"https://api.base44.com/apps/{APP_ID}/entities"
MATCHUP_ENTITY = "Matchup"
_ENV_KEY = "BASE44_API_KEY"

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Base44AuthError(RuntimeError):
    """Raised when no API key is available."""


class Base44Client:
    """Thin synchronous wrapper around the Base44 REST entity API.

    Every method maps directly to a CRUD operation on the ``Matchup`` entity
    inside the Axiom-60 Base44 app.

    Parameters
    ----------
    api_key:
        Base44 API key.  Obtain it from the Base44 app settings page.
    timeout:
        Per-request timeout in seconds (default 10).
    """

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        if not api_key:
            raise Base44AuthError("api_key must not be empty.")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, timeout: float = 10.0) -> "Base44Client":
        """Create a client using the ``BASE44_API_KEY`` environment variable.

        Raises :class:`Base44AuthError` if the variable is not set.
        """
        api_key = os.environ.get(_ENV_KEY, "")
        if not api_key:
            raise Base44AuthError(
                f"Environment variable {_ENV_KEY!r} is not set. "
                "Set it to your Base44 API key before calling this method."
            )
        return cls(api_key=api_key, timeout=timeout)

    # ------------------------------------------------------------------
    # Matchup CRUD
    # ------------------------------------------------------------------

    def list_matchups(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Return all Matchup records, with optional server-side filters.

        Parameters
        ----------
        filters:
            Optional key/value pairs forwarded to the Base44 API as query
            parameters (e.g. ``{"signal": "BET"}``).
        """
        url = f"{BASE_URL}/{MATCHUP_ENTITY}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.get(url, headers=self._headers, params=filters or {})
            response.raise_for_status()
        return response.json()

    def get_matchup(self, matchup_id: str) -> Dict[str, Any]:
        """Fetch a single Matchup by its Base44 entity ID."""
        url = f"{BASE_URL}/{MATCHUP_ENTITY}/{matchup_id}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.get(url, headers=self._headers)
            response.raise_for_status()
        return response.json()

    def create_matchup(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Matchup record in the Base44 app.

        Parameters
        ----------
        data:
            Dictionary containing at minimum the AXIOM-60 output fields:
            ``signal``, ``reason``, ``ba_gap``, ``abs_edge``, ``spread``,
            ``ou``.  Optional extra keys (e.g. team names, game date) are
            passed through unchanged.
        """
        url = f"{BASE_URL}/{MATCHUP_ENTITY}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.post(url, headers=self._headers, json=data)
            response.raise_for_status()
        return response.json()

    def update_matchup(self, matchup_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Partially update an existing Matchup record.

        Only the keys present in *data* are updated; all other fields are
        left unchanged.
        """
        url = f"{BASE_URL}/{MATCHUP_ENTITY}/{matchup_id}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.put(url, headers=self._headers, json=data)
            response.raise_for_status()
        return response.json()

    def delete_matchup(self, matchup_id: str) -> None:
        """Delete a Matchup record by its Base44 entity ID."""
        url = f"{BASE_URL}/{MATCHUP_ENTITY}/{matchup_id}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.delete(url, headers=self._headers)
            response.raise_for_status()
