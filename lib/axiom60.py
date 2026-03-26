"""
lib.axiom60 — public interface for the AXIOM-60 engine.

Re-exports :func:`run_axiom60` so callers can import from a stable,
non-scripts path:

    from lib.axiom60 import run_axiom60
"""

from scripts.axiom60 import run_axiom60  # noqa: F401  (re-export)

__all__ = ["run_axiom60"]
