# ==============================================================================
# File: p3_campaign_bridge.py
#
# Description:
# Handles the conversation flow for the P3 Campaign Recommendation
# pipeline. It collects geography and industry from the user,
# performs campaign lookup, generates recommendations, and updates
# the session state.
# ==============================================================================

from __future__ import annotations

from fastapi import BackgroundTasks

from apis.campaign_suggest.campaign_nlp import extract_geography, extract_industry
from apis.campaign_suggest.campaign_suggestions import (
    get_geography_suggestions,
    get_industry_suggestions,
)
from apis.campaign_suggest.campaign_cortex_service import find_similar_campaigns

from apis.p3_campaign.p3_session import (
    get_session,
    update_session,
    set_stage,
    STAGE_ASK_INDUSTRY,
    STAGE_FETCHING,
    STAGE_RECOMMENDATION_READY,
)

from apis.p3_campaign.p3_recommendation import generate_recommendation


# ==============================================================================
# Handle Geography Stage
# ==============================================================================

def handle_ask_geography(session_id: str, user_input: str) -> dict:
    """
    Extracts the geography from the user's input and moves the
    conversation to the industry stage.
    """

    geography = extract_geography(user_input)

    # --------------------------------------------------------------------------
    # Geography Not Found
    # --------------------------------------------------------------------------

    if not geography:
        return {
            "status": "in_progress",
            "stage": "ask_geography",
            "response": (
                "I didn't catch a specific geography. "
                "Which country or region are you targeting? "
                "For example: USA, Europe, India."
            ),
            "suggestions": {
                "geography": get_geography_suggestions()
            },
        }

    # --------------------------------------------------------------------------
    # Save Geography And Move To Industry Stage
    # --------------------------------------------------------------------------

    update_session(session_id, {"geography": geography})
    set_stage(session_id, STAGE_ASK_INDUSTRY)

    return {
        "status": "in_progress",
        "stage": STAGE_ASK_INDUSTRY,
        "response": f"Targeting {geography}. Which industry are you focusing on?",
        "suggestions": {
            "industry": get_industry_suggestions()
        },
    }


# ==============================================================================
# Handle Industry Stage
# ==============================================================================

def handle_ask_industry(
    session_id: str,
    user_input: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Extracts the industry from the user's input and starts the
    campaign lookup process.
    """

    industry = extract_industry(user_input)

    # --------------------------------------------------------------------------
    # Industry Not Found
    # --------------------------------------------------------------------------

    if not industry:
        return {
            "status": "in_progress",
            "stage": "ask_industry",
            "response": (
                "Could you be more specific about the industry? "
                "For example: Banking, Technology, Healthcare."
            ),
            "suggestions": {
                "industry": get_industry_suggestions()
            },
        }

    state = get_session(session_id)
    geography = state["geography"]

    # --------------------------------------------------------------------------
    # Save Industry And Start Background Processing
    # --------------------------------------------------------------------------

    update_session(session_id, {"industry": industry})
    set_stage(session_id, STAGE_FETCHING)

    background_tasks.add_task(
        _run_campaign_lookup,
        session_id=session_id,
        geography=geography,
        industry=industry,
        user_id=state.get("user_id"),
    )

    return {
        "status": "fetching",
        "stage": STAGE_FETCHING,
        "response": f"Analysing similar campaigns for {industry} in {geography}...",
    }


# ==============================================================================
# Background Campaign Lookup
# ==============================================================================

def _run_campaign_lookup(
    session_id: str,
    geography: str,
    industry: str,
    user_id: int | None,
) -> None:
    """
    Performs campaign lookup, generates recommendations,
    and stores the results in the session.
    """

    from apis.campaign_suggest.brand_category_service import (
        categorize_brand,
        UNCATEGORIZED,
    )

    state = get_session(session_id)
    selected_product = state.get("selected_product", "")

    # --------------------------------------------------------------------------
    # Determine Brand Category
    # --------------------------------------------------------------------------

    brand_category = None

    if selected_product:
        brand_category = categorize_brand(selected_product)

        if brand_category == UNCATEGORIZED:
            brand_category = None

    # --------------------------------------------------------------------------
    # Find Similar Campaigns
    # --------------------------------------------------------------------------

    matched_campaigns = []

    try:
        matched_campaigns = find_similar_campaigns(
            geography=geography,
            industry=industry,
            brand_category=brand_category,
            limit=5,
        )

        print(
            f"[P3Bridge] {len(matched_campaigns)} campaigns found for "
            f"{industry}/{geography}"
        )

    except Exception as e:
        print(f"[P3Bridge] Campaign lookup failed: {e}")

    # --------------------------------------------------------------------------
    # Generate Campaign Recommendation
    # --------------------------------------------------------------------------

    try:
        recommendation, display_campaigns = generate_recommendation(
            geography=geography,
            industry=industry,
            selected_product=selected_product,
            matched_campaigns=matched_campaigns,
            company_profile=None,
        )

    except Exception as e:
        print(f"[P3Bridge] Recommendation generation failed: {e}")

        recommendation = (
            f"For {industry} in {geography}, I recommend targeting "
            f"mid-to-senior level decision makers at relevant companies."
        )

        display_campaigns = _build_display_campaigns(matched_campaigns)

    # --------------------------------------------------------------------------
    # Update Session
    # --------------------------------------------------------------------------

    update_session(
        session_id,
        {
            "matched_campaigns": matched_campaigns,
            "display_campaigns": display_campaigns,
            "recommendation": recommendation,
        },
    )

    set_stage(session_id, STAGE_RECOMMENDATION_READY)

    print(f"[P3Bridge] Session {session_id} → recommendation_ready")


# ==============================================================================
# Build Campaign Display Data
# ==============================================================================

def _build_display_campaigns(
    matched_campaigns: list[dict],
) -> list[dict]:
    """
    Formats campaign records into a simplified structure
    for frontend display.
    """

    def _get(row, *keys):
        """
        Returns the first available value for the provided keys.
        """

        for key in keys:
            value = (
                row.get(key)
                or row.get(key.upper())
                or row.get(key.lower())
            )

            if value:
                return str(value).strip()

        return "Not specified"

    display = []

    for index, campaign in enumerate(matched_campaigns[:5]):
        display.append(
            {
                "index": index + 1,
                "job_level": _get(campaign, "job_level_desc"),
                "job_function": _get(campaign, "jobfunction_desc"),
                "employee_size": _get(campaign, "employee_size_desc"),
                "revenue_range": _get(campaign, "revenue_size_desc"),
                "geography": _get(campaign, "location_desc"),
                "quantity": _get(campaign, "effective_total_quantity"),
            }
        )

    return display