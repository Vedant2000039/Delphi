# routes.py
# ─────────────────────────────────────────────────────────────
# Context Engine — two-phase conversation pipeline.
#
# Phase 1 — PRODUCT UNDERSTANDING
#   Collects: product description, name, USPs, pricing tier,
#   campaign budget, ideal buyer, market type, buyer stage.
#
# Phase 2 — AUDIENCE TARGETING
#   Collects: geography, industry, job function, job level,
#   employee size, revenue range.
#
# Complete → Cortex → Insight Engine → AI Validator → results
#
# The /prefill endpoint is called by the campaign pipeline on
# handoff to pre-seed geography and industry so they are not
# re-collected from the user.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter
from pydantic import BaseModel

from .context_memory import (
    get_context,
    update_context,
    reset_context,
    is_complete,
    force_update_field,
    set_pending_edit,
    get_pending_edit,
    clear_pending_edit,
)

from .context_builder import build_context

from .ai_taxonomy_service import (
    get_next_field,
    get_conversation_phase,
    generate_conversational_question,
    generate_completion_message,
    PRODUCT_FIELDS,
    TARGETING_FIELDS,
    QUESTION_MAP,
    FIELD_LABELS,
)

from .intent_analyzer import (
    is_off_topic,
    generate_off_topic_reply,
    detect_edit_intent,
    extract_new_value_for_field,
)

from .openai_service import ask_gpt
from .prompt_builder import build_cortex_prompt
from .cortex_service import query_cortex_analyst
from .insight_engine import run_insight_engine
from .ai_validator import validate_and_enrich
from .suggestion_engine import get_suggestions

router = APIRouter(
    prefix="/context",
    tags=["Context Engine"],
)

ACTIVE_FIELD_ORDER = [
    *PRODUCT_FIELDS,
    "geography",
    "industry",
    "job_function",
    "job_level",
    "employee_size",
    "revenue_range",
]


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


class PrefillRequest(BaseModel):
    session_id: str
    context: dict


# ══════════════════════════════════════════════════════════════
# CHAT ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id
    user_input = req.message.strip()

    state   = get_context(session_id)
    context = state["context"]
    phase   = get_conversation_phase(context)

    # ── EDIT FLOW ─────────────────────────────────────────────
    # Case A: waiting for a new value after a previous edit request.
    pending_field = get_pending_edit(session_id)

    if pending_field:
        new_value = extract_new_value_for_field(user_input, pending_field)
        if new_value:
            force_update_field(session_id, pending_field, new_value)
            clear_pending_edit(session_id)
            context    = get_context(session_id)["context"]
            phase      = get_conversation_phase(context)
            next_field = get_next_field(context)
            field_label = FIELD_LABELS.get(pending_field, pending_field)
            confirm_msg = _generate_edit_confirmation(field_label, new_value, context)
            suggestions = (
                get_suggestions(context, next_field)
                if next_field and phase == "targeting" else {}
            )
            return {
                "status":       "in_progress" if next_field else "complete",
                "phase":        phase,
                "context":      context,
                "response":     confirm_msg,
                "suggestions":  suggestions,
                "next_field":   next_field,
                "edit_applied": {"field": pending_field, "value": new_value},
                "progress":     _progress(context),
            }
        else:
            field_label = FIELD_LABELS.get(pending_field, pending_field)
            return {
                "status":     "in_progress",
                "phase":      phase,
                "context":    context,
                "response":   f"What would you like to change {field_label} to?",
                "next_field": pending_field,
                "progress":   _progress(context),
            }

    # Case B: edit intent in a normal message.
    edit_field = detect_edit_intent(user_input)

    if edit_field:
        new_value = extract_new_value_for_field(user_input, edit_field)
        if new_value:
            force_update_field(session_id, edit_field, new_value)
            context     = get_context(session_id)["context"]
            phase       = get_conversation_phase(context)
            next_field  = get_next_field(context)
            field_label = FIELD_LABELS.get(edit_field, edit_field)
            confirm_msg = _generate_edit_confirmation(field_label, new_value, context)
            suggestions = (
                get_suggestions(context, next_field)
                if next_field and phase == "targeting" else {}
            )
            return {
                "status":       "in_progress" if next_field else "complete",
                "phase":        phase,
                "context":      context,
                "response":     confirm_msg,
                "suggestions":  suggestions,
                "next_field":   next_field,
                "edit_applied": {"field": edit_field, "value": new_value},
                "progress":     _progress(context),
            }
        else:
            set_pending_edit(session_id, edit_field)
            field_label = FIELD_LABELS.get(edit_field, edit_field)
            return {
                "status":     "in_progress",
                "phase":      phase,
                "context":    context,
                "response":   f"What would you like to change {field_label} to?",
                "next_field": edit_field,
                "progress":   _progress(context),
            }

    # ── NORMAL FLOW ───────────────────────────────────────────
    context = build_context(user_input, context, current_phase=phase)
    update_context(session_id, context)
    phase = get_conversation_phase(context)

    # Off-topic check (targeting phase only)
    if phase == "targeting" and is_off_topic(user_input):
        next_field        = get_next_field(context)
        fallback_question = QUESTION_MAP.get(next_field, "")
        reply             = generate_off_topic_reply(user_input, context, fallback_question)
        suggestions       = get_suggestions(context, next_field) if next_field else {}
        return {
            "status":      "in_progress",
            "phase":       phase,
            "context":     context,
            "response":    reply,
            "suggestions": suggestions,
            "next_field":  next_field,
            "off_topic":   True,
            "progress":    _progress(context),
        }

    print(f"[Session={session_id}] Phase={phase} Context={context}")

    next_field = get_next_field(context)

    if next_field:
        response    = generate_conversational_question(context, user_input, next_field)
        suggestions = (
            get_suggestions(context, next_field)
            if phase == "targeting" else {}
        )
        return {
            "status":      "in_progress",
            "phase":       phase,
            "context":     context,
            "response":    response,
            "suggestions": suggestions,
            "next_field":  next_field,
            "progress":    _progress(context),
        }

    # ── COLLECTION COMPLETE — run full pipeline ───────────────
    summary_msg   = generate_completion_message(context)
    cortex_prompt = build_cortex_prompt(context, user_input)

    try:
        cortex_leads = query_cortex_analyst(cortex_prompt)
        print(f"[Cortex] Returned {len(cortex_leads)} leads")
    except Exception as e:
        print(f"[Cortex Error] {e}")
        cortex_leads = []

    if not cortex_leads:
        return {
            "status":     "complete",
            "phase":      "complete",
            "context":    context,
            "summary":    summary_msg,
            "response":   (
                "No leads were returned for these criteria. "
                "Consider broadening your geography or industry filters."
            ),
            "leads":      [],
            "validation": {"valid": False, "notes": "No leads returned from Cortex."},
            "suggestions": {},
            "progress":   {"filled": len(ACTIVE_FIELD_ORDER), "total": len(ACTIVE_FIELD_ORDER), "percent": 100},
        }

    # Insight Engine
    try:
        scored_leads = run_insight_engine(cortex_leads)
        print(f"[InsightEngine] {len(scored_leads)} leads passed threshold")
    except Exception as e:
        print(f"[InsightEngine Error] {e}")
        scored_leads = cortex_leads

    if not scored_leads:
        return {
            "status":     "complete",
            "phase":      "complete",
            "context":    context,
            "summary":    summary_msg,
            "response":   (
                "Leads were found but none cleared the quality threshold. "
                "Try adjusting your targeting parameters."
            ),
            "leads":      [],
            "validation": {"valid": False, "notes": "No leads cleared the quality threshold."},
            "suggestions": {},
            "progress":   {"filled": len(ACTIVE_FIELD_ORDER), "total": len(ACTIVE_FIELD_ORDER), "percent": 100},
        }

    # AI Validator + enrichment
    try:
        enriched = validate_and_enrich(context, scored_leads)
    except Exception as e:
        print(f"[AIValidator Error] {e}")
        enriched = {
            "summary":    summary_msg,
            "validation": {"valid": True, "notes": ""},
            "leads":      scored_leads,
        }

    return {
        "status":     "complete",
        "phase":      "complete",
        "context":    context,
        "summary":    enriched.get("summary", summary_msg),
        "validation": enriched.get("validation", {}),
        "leads":      enriched.get("leads", []),
        "suggestions": {},
        "progress":   {"filled": len(ACTIVE_FIELD_ORDER), "total": len(ACTIVE_FIELD_ORDER), "percent": 100},
    }


# ══════════════════════════════════════════════════════════════
# PREFILL — called by campaign pipeline on handoff
# ══════════════════════════════════════════════════════════════

@router.post("/prefill")
def prefill_context(req: PrefillRequest):
    """
    Pre-seeds the lead pipeline context with values from the campaign
    pipeline handoff (geography + industry). Only sets fields that are
    not already filled so existing context is never overwritten.
    """
    state    = get_context(req.session_id)
    existing = state["context"]

    for field, value in req.context.items():
        if value and str(value).strip() and not existing.get(field):
            existing[field] = str(value).strip()

    update_context(req.session_id, existing)

    return {
        "status":  "prefilled",
        "context": get_context(req.session_id)["context"],
    }


# ══════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.post("/reset")
def reset(req: ResetRequest):
    reset_context(req.session_id)
    return {"status": "reset", "session_id": req.session_id}


@router.get("/context/{session_id}")
def get_session_context(session_id: str):
    state   = get_context(session_id)
    context = state["context"]
    return {
        "session_id":    session_id,
        "phase":         get_conversation_phase(context),
        "context":       context,
        "message_count": state.get("message_count", 0),
        "complete":      is_complete(session_id),
    }


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _progress(context: dict) -> dict:
    filled = sum(1 for field in ACTIVE_FIELD_ORDER if context.get(field))
    total  = len(ACTIVE_FIELD_ORDER)
    return {
        "filled":  filled,
        "total":   total,
        "percent": round((filled / total) * 100),
    }


def _generate_edit_confirmation(
    field_label: str,
    new_value: str,
    context: dict,
) -> str:
    next_field = get_next_field(context)
    next_q     = QUESTION_MAP.get(next_field, "") if next_field else ""

    prompt = f"""You are Delphi, a B2B campaign intelligence assistant.

The user updated a field: {field_label} has been set to "{new_value}".
{"Next question: " + next_q if next_q else "All fields are now complete."}

Write one short response (1-2 sentences) that:
1. Acknowledges the update naturally — not mechanically
2. Asks the next question if one exists, or confirms everything is complete

No filler. Consultative tone."""

    try:
        return ask_gpt(prompt, temperature=0.5, max_tokens=100)
    except Exception:
        base = f"{field_label} updated to \"{new_value}\"."
        return f"{base} {next_q}" if next_q else base