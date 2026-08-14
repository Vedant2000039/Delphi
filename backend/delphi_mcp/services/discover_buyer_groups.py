"""
discover_buyer_groups.py

MCP tool: discover_buyer_groups

Mirrors the discover_icp pipeline shape:

    read brand context (from prior product/brand match, same as ICP)
        -> Usp_get_buyer_groups (buyer_group_service.py)
        -> GPT-4.1 semantic grouping (buyer_group_grouper.py)
        -> frontend-safe JSON (roles / goals / decision_influence / insight)

Depends on ICP having already run in this session (brand_id comes from
the same brand-matching step discover_icp uses) — per the design doc,
Buyer Groups should be scoped to the ICP-qualified population, not the
entire CRM.

As with discover_icp: raw lead records never leave this function. Only
buyer_group_service's aggregated rows and the LLM's named groups do.
"""

import logging

try:
    from buyer_group_engine.buyer_group_service import get_buyer_group_candidates
    from buyer_group_engine.buyer_group_grouper import generate_buyer_groups
except ImportError:
    from ..buyer_group_engine.buyer_group_service import get_buyer_group_candidates
    from ..buyer_group_engine.buyer_group_grouper import generate_buyer_groups

logger = logging.getLogger("discover_buyer_groups")


def discover_buyer_groups(brand_id: int, brand_name: str = "", product_name: str = "") -> dict:
    """
    MCP tool entrypoint.

    Args:
        brand_id: the brand whose qualified leads should be analyzed.
                   Same brand_id already resolved during discover_icp's
                   product -> brand matching step.
        brand_name / product_name: display context, passed to the LLM
                   prompt for better naming (e.g. "MacBook Pro" flavors
                   the roles it infers), purely cosmetic — not filters.

    Returns:
        {
            "status": "ok" | "no_data",
            "buyer_groups": [
                {
                    "group_name": "IT & Infrastructure",
                    "roles": [...],
                    "goals": [...],
                    "decision_influence": "HIGH",
                    "decision_role": "Evaluator",
                    "why_this_group": "..."
                },
                ...
            ],
            "insight": "..."
        }
    """
    candidates = get_buyer_group_candidates(brand_id)

    if not candidates:
        logger.info("discover_buyer_groups: no candidates for brand_id=%s", brand_id)
        return {
            "status": "no_data",
            "buyer_groups": [],
            "insight": "We don't have enough qualified leads yet to map buyer groups for this ICP.",
        }

    result = generate_buyer_groups(candidates, brand_name=brand_name, product_name=product_name)

    return {
        "status": "ok",
        "buyer_groups": result.get("buyer_groups", []),
        "insight": result.get("insight", ""),
    }