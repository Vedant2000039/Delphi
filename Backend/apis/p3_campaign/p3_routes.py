# apis/p3_campaign/p3_routes.py
from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from apis.p3_campaign.p3_session import (
    get_session, update_session, set_stage, reset_session,
    get_next_path_c_field, path_c_complete, update_path_c,
    build_final_context, PATH_C_FIELDS,
    STAGE_ASK_PRODUCT, STAGE_ASK_GEOGRAPHY, STAGE_ASK_INDUSTRY,
    STAGE_FETCHING, STAGE_RECOMMENDATION_READY,
    STAGE_AWAITING_MODIFICATION, STAGE_AWAITING_CONFIRMATION,
    STAGE_PATH_C_COLLECTING, STAGE_COMPLETE,
)
from apis.p3_campaign.p3_product_selector import (
    get_user_products, detect_product_selection, build_product_question,
)
from apis.p3_campaign.p3_campaign_bridge import (
    handle_ask_geography, handle_ask_industry,
)
from apis.p3_campaign.p3_paths import (
    detect_path, detect_campaign_selection, extract_modifications,
    build_targeting_from_campaign, apply_overrides, format_targeting_summary,
)
from apis.campaign_suggest.campaign_suggestions import get_geography_suggestions
from apis.context_engine.suggestion_engine      import get_suggestions

router = APIRouter(prefix="/p3", tags=["Pipeline 3 — Campaign"])


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str
    message:    str
    user_id:    int

class ResetRequest(BaseModel):
    session_id: str


# ══════════════════════════════════════════════════════════════
# POST /p3/chat
# ══════════════════════════════════════════════════════════════

@router.post("/chat")
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id
    user_input = req.message.strip()
    state      = get_session(session_id, user_id=req.user_id)
    stage      = state["stage"]

    if stage == STAGE_ASK_PRODUCT:
        return _handle_ask_product(session_id, user_input, req.user_id)

    if stage == STAGE_ASK_GEOGRAPHY:
        return handle_ask_geography(session_id, user_input)

    if stage == STAGE_ASK_INDUSTRY:
        return handle_ask_industry(session_id, user_input, background_tasks)

    if stage == STAGE_FETCHING:
        return {
            "status":   "fetching",
            "stage":    STAGE_FETCHING,
            "response": "Still analysing similar campaigns, hang tight...",
        }

    if stage == STAGE_RECOMMENDATION_READY:
        return _handle_recommendation_response(session_id, user_input)

    if stage == STAGE_AWAITING_MODIFICATION:
        return _handle_free_modification(session_id, user_input)

    if stage == STAGE_AWAITING_CONFIRMATION:
        return _handle_confirmation(session_id, user_input)

    if stage == STAGE_PATH_C_COLLECTING:
        return _handle_path_c(session_id, user_input)

    if stage == STAGE_COMPLETE:
        return {
            "status":        "complete",
            "stage":         STAGE_COMPLETE,
            "response":      "Your targeting profile is ready.",
            "final_context": state["final_context"],
        }

    reset_session(session_id)
    return {
        "status":   "reset",
        "response": "Something went wrong. Let's start over — what product would you like to run a campaign for?",
    }


# ══════════════════════════════════════════════════════════════
# STAGE HANDLERS
# ══════════════════════════════════════════════════════════════

def _handle_ask_product(session_id: str, user_input: str, user_id: int) -> dict:
    state    = get_session(session_id)
    products = get_user_products(user_id)          # flat list[str]

    # First visit — show product list
    if state.get("selected_product") is None and not _looks_like_product_answer(user_input):
        question = build_product_question(products)
        update_session(session_id, {"_products_shown": products})
        return {
            "status":      "in_progress",
            "stage":       STAGE_ASK_PRODUCT,
            "response":    question,
            "suggestions": products,
        }

    # User is answering — match against known products
    known_products = state.get("_products_shown") or products
    matched        = detect_product_selection(user_input, known_products)
    product_value  = matched if matched else user_input.strip()

    update_session(session_id, {"selected_product": product_value})
    set_stage(session_id, STAGE_ASK_GEOGRAPHY)

    return {
        "status":      "in_progress",
        "stage":       STAGE_ASK_GEOGRAPHY,
        "response":    (
            f"Got it — running a campaign for \"{product_value}\". "
            f"Which geography are you targeting?"
        ),
        "suggestions": {"geography": get_geography_suggestions()},
    }


def _handle_recommendation_response(session_id: str, user_input: str) -> dict:
    state             = get_session(session_id)
    display_campaigns = state["display_campaigns"]
    path              = detect_path(user_input, display_campaigns)

    # ── PATH A ───────────────────────────────────────────────
    if path == "accept":
        idx = detect_campaign_selection(user_input, display_campaigns)
        if idx is None:
            return {
                "status":   "in_progress",
                "stage":    STAGE_RECOMMENDATION_READY,
                "response": "Which campaign would you like to go with? Just say the number — 1, 2, 3, 4, or 5.",
            }

        targeting = build_targeting_from_campaign(display_campaigns[idx])
        final_context = build_final_context(
            product=state["selected_product"],
            geography=state["geography"],
            industry=state["industry"],
            targeting=targeting,
        )
        update_session(session_id, {"final_context": final_context})
        set_stage(session_id, STAGE_COMPLETE)

        summary = format_targeting_summary(
            product=state["selected_product"],
            geography=state["geography"],
            industry=state["industry"],
            targeting=targeting,
        )
        return {
            "status":        "complete",
            "stage":         STAGE_COMPLETE,
            "response":      f"Campaign {idx+1} selected. Here's your targeting profile:\n\n{summary}\n\nReady to find leads.",
            "final_context": final_context,
        }

    # ── PATH B1 ──────────────────────────────────────────────
    if path == "modify_campaign":
        idx = detect_campaign_selection(user_input, display_campaigns)
        if idx is None:
            set_stage(session_id, STAGE_AWAITING_MODIFICATION)
            update_session(session_id, {"pending_base_index": None})
            return {
                "status":   "in_progress",
                "stage":    STAGE_AWAITING_MODIFICATION,
                "response": "Which campaign would you like to use as a base? Say the number (1–5), then tell me what you'd like to change.",
            }

        base_targeting = build_targeting_from_campaign(display_campaigns[idx])
        overrides      = extract_modifications(user_input)
        merged         = apply_overrides(base_targeting, overrides)

        update_session(session_id, {
            "pending_base_index": idx,
            "pending_context":    merged,
        })
        set_stage(session_id, STAGE_AWAITING_CONFIRMATION)

        summary = format_targeting_summary(
            product=state["selected_product"],
            geography=state["geography"],
            industry=state["industry"],
            targeting=merged,
        )
        changes_text = (
            f" with {', '.join(f'{k} → {v}' for k, v in overrides.items())}"
            if overrides else ""
        )
        return {
            "status":   "in_progress",
            "stage":    STAGE_AWAITING_CONFIRMATION,
            "response": f"Using Campaign {idx+1} as base{changes_text}.\n\n{summary}\n\nAnything else to adjust, or shall I find leads?",
        }

    # ── PATH B2 ──────────────────────────────────────────────
    if path == "modify_free":
        set_stage(session_id, STAGE_AWAITING_MODIFICATION)
        return {
            "status":   "in_progress",
            "stage":    STAGE_AWAITING_MODIFICATION,
            "response": "What kind of modifications are you looking for? For example: different job level, company size, or revenue range.",
        }

    # ── PATH C ───────────────────────────────────────────────
    if path == "reject":
        set_stage(session_id, STAGE_PATH_C_COLLECTING)
        update_session(session_id, {"path_c_context": {}})
        first_field = PATH_C_FIELDS[0]
        return {
            "status":      "in_progress",
            "stage":       STAGE_PATH_C_COLLECTING,
            "response":    (
                "No problem — since this is a new targeting profile, "
                "I'll need a few details from you.\n\n"
                f"{_path_c_question(first_field)}"
            ),
            "suggestions": _path_c_suggestions(first_field),
            "next_field":  first_field,
        }

    return {
        "status":   "in_progress",
        "stage":    STAGE_RECOMMENDATION_READY,
        "response": "Could you clarify? You can select a campaign (1–5), ask for modifications, or start fresh.",
    }


def _handle_free_modification(session_id: str, user_input: str) -> dict:
    state     = get_session(session_id)
    extracted = extract_modifications(user_input)

    if not extracted:
        return {
            "status":   "in_progress",
            "stage":    STAGE_AWAITING_MODIFICATION,
            "response": (
                "I couldn't extract specific details from that. "
                "Could you be more specific? For example: "
                "'C-Suite Finance leads at enterprise companies above $1B revenue'."
            ),
        }

    pending_base_idx = state.get("pending_base_index")
    if pending_base_idx is not None:
        base = build_targeting_from_campaign(state["display_campaigns"][pending_base_idx])
        merged = apply_overrides(base, extracted)
    else:
        merged = extracted

    update_session(session_id, {"pending_context": merged})
    set_stage(session_id, STAGE_AWAITING_CONFIRMATION)

    summary = format_targeting_summary(
        product=state["selected_product"],
        geography=state["geography"],
        industry=state["industry"],
        targeting=merged,
    )
    return {
        "status":   "in_progress",
        "stage":    STAGE_AWAITING_CONFIRMATION,
        "response": f"Got it. Here's your targeting profile:\n\n{summary}\n\nAnything else to adjust, or shall I find leads?",
    }


def _handle_confirmation(session_id: str, user_input: str) -> dict:
    state = get_session(session_id)
    lower = user_input.lower()

    _CONFIRM  = ("yes", "yeah", "go ahead", "looks good", "that's it",
                 "find leads", "continue", "confirm", "proceed",
                 "perfect", "done", "correct", "right", "good")
    _CHANGES  = ("change", "update", "modify", "adjust", "actually",
                 "but", "instead", "different", "not quite")

    wants_more = any(kw in lower for kw in _CHANGES)
    confirms   = any(kw in lower for kw in _CONFIRM)

    if wants_more and not confirms:
        new_overrides = extract_modifications(user_input)
        if new_overrides:
            merged = apply_overrides(state.get("pending_context", {}), new_overrides)
            update_session(session_id, {"pending_context": merged})
            summary = format_targeting_summary(
                product=state["selected_product"],
                geography=state["geography"],
                industry=state["industry"],
                targeting=merged,
            )
            changes = ", ".join(f"{k} → {v}" for k, v in new_overrides.items())
            return {
                "status":   "in_progress",
                "stage":    STAGE_AWAITING_CONFIRMATION,
                "response": f"Updated — {changes}.\n\n{summary}\n\nAnything else, or shall I find leads?",
            }
        else:
            set_stage(session_id, STAGE_AWAITING_MODIFICATION)
            return {
                "status":   "in_progress",
                "stage":    STAGE_AWAITING_MODIFICATION,
                "response": "What would you like to change? For example: job level, company size, or revenue range.",
            }

    targeting     = state.get("pending_context", {})
    final_context = build_final_context(
        product=state["selected_product"],
        geography=state["geography"],
        industry=state["industry"],
        targeting=targeting,
    )
    update_session(session_id, {"final_context": final_context})
    set_stage(session_id, STAGE_COMPLETE)

    summary = format_targeting_summary(
        product=state["selected_product"],
        geography=state["geography"],
        industry=state["industry"],
        targeting=targeting,
    )
    return {
        "status":        "complete",
        "stage":         STAGE_COMPLETE,
        "response":      f"Here's your final targeting profile:\n\n{summary}\n\nReady to find leads.",
        "final_context": final_context,
    }


def _handle_path_c(session_id: str, user_input: str) -> dict:
    next_field = get_next_path_c_field(session_id)

    if not next_field:
        return _finalize_path_c(session_id)

    extracted = extract_modifications(user_input).get(next_field)

    if not extracted:
        return {
            "status":      "in_progress",
            "stage":       STAGE_PATH_C_COLLECTING,
            "response":    f"I didn't catch that. {_path_c_question(next_field)}",
            "suggestions": _path_c_suggestions(next_field),
            "next_field":  next_field,
        }

    update_path_c(session_id, next_field, extracted)

    if path_c_complete(session_id):
        return _finalize_path_c(session_id)

    next_next = get_next_path_c_field(session_id)
    return {
        "status":      "in_progress",
        "stage":       STAGE_PATH_C_COLLECTING,
        "response":    _path_c_question(next_next),
        "suggestions": _path_c_suggestions(next_next),
        "next_field":  next_next,
    }


def _finalize_path_c(session_id: str) -> dict:
    state         = get_session(session_id)
    final_context = build_final_context(
        product=state["selected_product"],
        geography=state["geography"],
        industry=state["industry"],
        targeting=state.get("path_c_context", {}),
    )
    update_session(session_id, {"final_context": final_context})
    set_stage(session_id, STAGE_COMPLETE)

    summary = format_targeting_summary(
        product=state["selected_product"],
        geography=state["geography"],
        industry=state["industry"],
        targeting=state.get("path_c_context", {}),
    )
    return {
        "status":        "complete",
        "stage":         STAGE_COMPLETE,
        "response":      f"Here's your targeting profile:\n\n{summary}\n\nReady to find leads.",
        "final_context": final_context,
    }


# ══════════════════════════════════════════════════════════════
# GET /p3/status/{session_id}
# ══════════════════════════════════════════════════════════════

@router.get("/status/{session_id}")
def get_status(session_id: str):
    state = get_session(session_id)
    return {"session_id": session_id, "stage": state["stage"]}


# ══════════════════════════════════════════════════════════════
# GET /p3/recommendation/{session_id}
# ══════════════════════════════════════════════════════════════

@router.get("/recommendation/{session_id}")
def get_recommendation(session_id: str):
    state = get_session(session_id)
    if state["stage"] != STAGE_RECOMMENDATION_READY:
        raise HTTPException(
            status_code=400,
            detail=f"Recommendation not ready. Current stage: {state['stage']}"
        )
    display_campaigns = state["display_campaigns"]
    quick_replies = (
        [f"Select campaign {c['index']}" for c in display_campaigns]
        + ["I want modifications", "Start fresh"]
    )
    return {
        "status":        "recommendation_ready",
        "stage":         STAGE_RECOMMENDATION_READY,
        "response":      state["recommendation"],
        "campaigns":     display_campaigns,
        "quick_replies": quick_replies,
    }


# ══════════════════════════════════════════════════════════════
# POST /p3/reset
# ══════════════════════════════════════════════════════════════

@router.post("/reset")
def reset(req: ResetRequest):
    reset_session(req.session_id)
    return {"status": "reset", "session_id": req.session_id}


# ══════════════════════════════════════════════════════════════
# GET /p3/session/{session_id}  — debug
# ══════════════════════════════════════════════════════════════

@router.get("/session/{session_id}")
def debug_session(session_id: str):
    state = get_session(session_id)
    safe  = {k: v for k, v in state.items() if k != "matched_campaigns"}
    safe["matched_campaigns_count"] = len(state.get("matched_campaigns", []))
    return safe


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

_PATH_C_QUESTIONS = {
    "job_function":  "Which department or job function are you targeting? (e.g. Finance, Marketing, Engineering)",
    "job_level":     "What seniority level should we focus on? (e.g. C-Suite, VP, Director, Manager)",
    "employee_size": "What company size are you targeting? (e.g. Mid-size, Enterprise, Small business)",
    "revenue_range": "What annual revenue range should the companies have? (e.g. $50M–$500M, >$1B)",
}

def _path_c_question(field: str) -> str:
    return _PATH_C_QUESTIONS.get(field, f"What is your preference for {field}?")

def _path_c_suggestions(field: str) -> dict:
    try:
        return get_suggestions({}, field)
    except Exception:
        return {}

def _looks_like_product_answer(text: str) -> bool:
    campaign_intents = (
        "campaign", "run a", "launch a", "start a",
        "find leads", "i want to", "help me",
    )
    return not any(kw in text.lower() for kw in campaign_intents)