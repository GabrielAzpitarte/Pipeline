"""Architecture taxonomy — strategy family classification.

Defines strategy families as first-class objects so the system can
measure diversity, detect saturation, and avoid pseudo-novelty.
"""

from __future__ import annotations

import re

ARCHITECTURE_FAMILIES: dict[str, dict[str, str]] = {
    "passive_maker": {
        "description": "Wide passive quotes, inventory skew, no aggressive taking",
        "alpha_source": "spread capture from passive fills",
        "transfer_risk": "high — passive fills unreliable on platform",
        "failure_mode": "queue-fragile, simulator-artifact",
    },
    "taker_pennying": {
        "description": "Penny quotes (bb+1/ba-1) + aggressive taking of mispriced orders",
        "alpha_source": "spread improvement + mispricing capture",
        "transfer_risk": "medium — penny fills depend on queue position",
        "failure_mode": "passive-fragile at tight spreads",
    },
    "bifurcated_specialist": {
        "description": "Different logic per asset type (stationary vs drifting)",
        "alpha_source": "asset-specific alpha extraction",
        "transfer_risk": "medium — depends on asset classification accuracy",
        "failure_mode": "one asset carrying all PnL",
    },
    "mean_reversion_sniper": {
        "description": "Fades price moves, exploits mean reversion",
        "alpha_source": "reversion after overreaction",
        "transfer_risk": "low-medium — reversion is a real market property",
        "failure_mode": "trending markets, regime changes",
    },
    "pure_taker": {
        "description": "Only takes mispriced orders, no passive quoting",
        "alpha_source": "pure mispricing capture",
        "transfer_risk": "low — aggressive fills are more reliable",
        "failure_mode": "few opportunities, low fill count",
    },
    "hybrid_assembled": {
        "description": "Combined from best-per-asset components",
        "alpha_source": "portfolio of asset-specific edges",
        "transfer_risk": "depends on components",
        "failure_mode": "cross-asset interference, state conflicts",
    },
}


def classify_strategy(code: str, description: str = "") -> str:
    """Classify a strategy into an architecture family using heuristics.

    Uses keyword patterns in the code and description to determine the
    most likely family. Returns the family key.
    """
    text = (code + " " + description).lower()

    # Check for assembled/hybrid first (most specific)
    if "assembled" in text or "combined" in text or "hybrid" in text:
        return "hybrid_assembled"

    # Check for bifurcated (per-asset specialization)
    if "bifurcated" in text or (
        re.search(r'symbol\s*==\s*"EMERALDS"', code, re.IGNORECASE)
        and re.search(r'symbol\s*==\s*"TOMATOES"', code, re.IGNORECASE)
    ):
        return "bifurcated_specialist"

    # Check for pure taker (no passive quoting)
    has_penny = "bb + 1" in code or "bb+1" in code or "ba - 1" in code or "ba-1" in code
    has_taker = "< fair" in code or "> fair" in code or "mispriced" in text
    if has_taker and not has_penny:
        return "pure_taker"

    # Check for mean reversion
    if "reversion" in text or "fade" in text or "autocorr" in text:
        return "mean_reversion_sniper"

    # Check for taker + pennying (most common)
    if has_penny and has_taker:
        return "taker_pennying"
    if has_penny:
        return "taker_pennying"

    # Default: passive maker
    return "passive_maker"


def get_family_info(family: str) -> dict[str, str]:
    """Get description and metadata for a family."""
    return ARCHITECTURE_FAMILIES.get(family, {"description": "Unknown family"})
