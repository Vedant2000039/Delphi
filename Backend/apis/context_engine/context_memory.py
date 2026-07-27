# context_memory.py
# In-memory store keyed by session_id
SESSION_STATE: dict[str, dict] = {}

# ── Required fields per phase ─────────────────────────────────
# industry_domain is intentionally excluded (not asked for now).

PRODUCT_FIELDS = [
    "product_description",
    "product_name",
    "product_usps",
    "product_pricing_tier",
    "campaign_budget",
    "ideal_buyer",
    "target_market_type",
    "buyer_stage",
]

TARGETING_FIELDS = [
    "geography",
    "industry",
    "job_function",
    "job_level",
    "employee_size",
    "revenue_range",
]

REQUIRED_FIELDS = PRODUCT_FIELDS + TARGETING_FIELDS


# ── Session lifecycle ─────────────────────────────────────────

def get_context(session_id: str) -> dict:
    """Get or initialise session state."""
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {
            "context": {},
            "conversation_stage": "product",
            "message_count": 0,
            # Tracks when we're waiting for a new value after an edit request.
            # Format: field name string, or None.
            "pending_edit_field": None,
        }
    return SESSION_STATE[session_id]


def update_context(session_id: str, new_data: dict) -> dict:
    """
    Merge new_data into session context.
    Normal mode: never overwrites an existing value (append-only).
    Use force_update_field() to overwrite during an edit flow.
    """
    state = get_context(session_id)
    for k, v in new_data.items():
        if v and str(v).strip():
            if not state["context"].get(k):        # never overwrite normally
                state["context"][k] = str(v).strip()
    state["message_count"] += 1
    return state


def force_update_field(session_id: str, field: str, value: str) -> dict:
    """
    Overwrite a specific field — used exclusively by the edit flow.
    Clears pending_edit_field after writing.
    """
    state = get_context(session_id)
    if value and str(value).strip():
        state["context"][field] = str(value).strip()
    state["pending_edit_field"] = None
    state["message_count"] += 1
    return state


def set_pending_edit(session_id: str, field: str) -> None:
    """Mark that we're waiting for the user to provide a new value for `field`."""
    state = get_context(session_id)
    state["pending_edit_field"] = field


def get_pending_edit(session_id: str) -> str | None:
    """Return the field currently awaiting a new value, or None."""
    return get_context(session_id).get("pending_edit_field")


def clear_pending_edit(session_id: str) -> None:
    get_context(session_id)["pending_edit_field"] = None


def reset_context(session_id: str) -> None:
    """Clear all session data (for a new conversation)."""
    if session_id in SESSION_STATE:
        del SESSION_STATE[session_id]


# ── Field / phase status helpers ──────────────────────────────

def get_missing_fields(session_id: str) -> list[str]:
    ctx = get_context(session_id)["context"]
    return [f for f in REQUIRED_FIELDS if not ctx.get(f)]


def get_missing_product_fields(session_id: str) -> list[str]:
    ctx = get_context(session_id)["context"]
    return [f for f in PRODUCT_FIELDS if not ctx.get(f)]


def get_missing_targeting_fields(session_id: str) -> list[str]:
    ctx = get_context(session_id)["context"]
    return [f for f in TARGETING_FIELDS if not ctx.get(f)]


def is_product_phase_complete(session_id: str) -> bool:
    return len(get_missing_product_fields(session_id)) == 0


def is_complete(session_id: str) -> bool:
    return len(get_missing_fields(session_id)) == 0


def get_phase(session_id: str) -> str:
    if not is_product_phase_complete(session_id):
        return "product"
    if not is_complete(session_id):
        return "targeting"
    return "complete"