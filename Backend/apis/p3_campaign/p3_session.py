# apis/p3_campaign/p3_session.py

from __future__ import annotations

# ------------------------------------------------------------------
# Pipeline stage constants
# ------------------------------------------------------------------

# Initial product selection stage
STAGE_ASK_PRODUCT = "ask_product"

# Geography selection stage
STAGE_ASK_GEOGRAPHY = "ask_geography"

# Industry selection stage
STAGE_ASK_INDUSTRY = "ask_industry"

# Background campaign lookup is running
STAGE_FETCHING = "fetching"

# Campaign recommendation is ready
STAGE_RECOMMENDATION_READY = "recommendation_ready"

# Waiting for user modification details (Path B2)
STAGE_AWAITING_MODIFICATION = "awaiting_modification"

# Waiting for recommendation confirmation (Path B1/B2)
STAGE_AWAITING_CONFIRMATION = "awaiting_confirmation"

# Collecting manual targeting information (Path C)
STAGE_PATH_C_COLLECTING = "path_c_collecting"

# Pipeline completed
STAGE_COMPLETE = "complete"


# ------------------------------------------------------------------
# Path C targeting fields
# ------------------------------------------------------------------

# These fields are collected one by one during Path C.
# Product, geography, and industry are already known.
PATH_C_FIELDS = [
    "job_function",
    "job_level",
    "employee_size",
    "revenue_range",
]


# ------------------------------------------------------------------
# In-memory session storage
# ------------------------------------------------------------------

_SESSIONS: dict[str, dict] = {}


# ------------------------------------------------------------------
# Session lifecycle methods
# ------------------------------------------------------------------

def get_session(session_id: str, user_id: int | None = None) -> dict:
    """
    Returns the existing session or creates a new Pipeline 3 session.
    The user_id is only used during initial session creation.
    """
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {

            # Current pipeline stage
            "stage": STAGE_ASK_PRODUCT,

            # Logged-in user
            "user_id": user_id,

            # Selected product/service
            "selected_product": None,

            # Targeting information
            "geography": None,
            "industry": None,

            # Campaign lookup results
            "matched_campaigns": [],
            "display_campaigns": [],

            # Recommendation text
            "recommendation": None,

            # Pending confirmation details
            "pending_base_index": None,
            "pending_context": {},

            # Manual targeting values (Path C)
            "path_c_context": {},

            # Final targeting context
            "final_context": {},
        }

    return _SESSIONS[session_id]


def update_session(session_id: str, updates: dict) -> dict:
    """
    Updates the session with the provided values.
    """
    state = get_session(session_id)
    state.update(updates)
    return state


def set_stage(session_id: str, stage: str) -> None:
    """
    Updates the current pipeline stage.
    """
    get_session(session_id)["stage"] = stage


def get_stage(session_id: str) -> str:
    """
    Returns the current pipeline stage.
    """
    return get_session(session_id).get(
        "stage",
        STAGE_ASK_PRODUCT,
    )


def reset_session(session_id: str) -> None:
    """
    Removes the session from memory.
    """
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]


# ------------------------------------------------------------------
# Path C helper methods
# ------------------------------------------------------------------

def get_next_path_c_field(session_id: str) -> str | None:
    """
    Returns the next Path C field that has not yet been collected.
    """
    context = get_session(session_id).get("path_c_context", {})

    for field in PATH_C_FIELDS:
        if not context.get(field):
            return field

    return None


def path_c_complete(session_id: str) -> bool:
    """
    Returns True when all Path C fields have been collected.
    """
    return get_next_path_c_field(session_id) is None


def update_path_c(session_id: str, field: str, value: str) -> None:
    """
    Stores a collected Path C field value.
    """
    state = get_session(session_id)
    state["path_c_context"][field] = value


# ------------------------------------------------------------------
# Final targeting context builder
# ------------------------------------------------------------------

def build_final_context(
    product: str,
    geography: str,
    industry: str,
    targeting: dict,
) -> dict:
    """
    Builds the final targeting context returned to the frontend.
    """
    return {
        "product": product,
        "geography": geography,
        "industry": industry,
        "job_level": targeting.get("job_level") or None,
        "job_function": targeting.get("job_function") or None,
        "employee_size": targeting.get("employee_size") or None,
        "revenue_range": targeting.get("revenue_range") or None,
    }