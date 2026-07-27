# ==============================================================================
# File: campaign_memory.py
#
# Description:
# This module manages the in-memory session state for the
# Campaign Suggestion Pipeline.
#
# Pipeline Stages:
#   ask_geography   - Waiting for the user to provide geography.
#   ask_industry    - Waiting for the user to provide industry.
#   show_campaigns  - Displaying matched campaigns.
#   await_icp       - Waiting for user confirmation to explore ICP.
#   show_icp        - Displaying ICP details for the selected campaign.
#   handoff         - Transitioning to the Context/Lead pipeline.
# ==============================================================================

from __future__ import annotations


# ==============================================================================
# Campaign Pipeline Stage Constants
# ==============================================================================

STAGE_ASK_GEO = "ask_geography"
STAGE_ASK_INDUSTRY = "ask_industry"
STAGE_SHOW_CAMPAIGNS = "show_campaigns"
STAGE_AWAIT_ICP = "await_icp"
STAGE_SHOW_ICP = "show_icp"
STAGE_HANDOFF = "handoff"


# ==============================================================================
# In-Memory Session Store
# ==============================================================================

CAMPAIGN_SESSIONS: dict[str, dict] = {}


# ==============================================================================
# Create Empty Campaign Session
# ==============================================================================

def _empty_session() -> dict:
    """
    Creates a new campaign session with default values.
    """
    return {
        "brand": None,
        "geography": None,
        "industry": None,
        "stage": STAGE_ASK_GEO,
        "matched_campaigns": [],
        "selected_campaign": None,
        "icp_data": None,
    }


# ==============================================================================
# Get Campaign Session
# ==============================================================================

def get_campaign_session(session_id: str) -> dict:
    """
    Returns the campaign session for the given session ID.
    If the session does not exist, a new one is created.
    """
    if session_id not in CAMPAIGN_SESSIONS:
        CAMPAIGN_SESSIONS[session_id] = _empty_session()

    return CAMPAIGN_SESSIONS[session_id]


# ==============================================================================
# Update Campaign Session
# ==============================================================================

def update_campaign_session(session_id: str, **kwargs) -> dict:
    """
    Updates one or more values in the campaign session.
    """
    state = get_campaign_session(session_id)

    for key, value in kwargs.items():
        state[key] = value

    return state


# ==============================================================================
# Reset Campaign Session
# ==============================================================================

def reset_campaign_session(session_id: str) -> None:
    """
    Removes the campaign session from memory.
    """
    if session_id in CAMPAIGN_SESSIONS:
        del CAMPAIGN_SESSIONS[session_id]


# ==============================================================================
# Check Campaign Pipeline Status
# ==============================================================================

def is_campaign_pipeline_active(session_id: str) -> bool:
    """
    Returns True if the session is still within the campaign pipeline
    and has not yet reached the handoff stage.
    """
    if session_id not in CAMPAIGN_SESSIONS:
        return False

    return CAMPAIGN_SESSIONS[session_id]["stage"] != STAGE_HANDOFF