# routes.py
# ─────────────────────────────────────────────────────────────
# Full pipeline per chat message:
#   0. Intent Engine — intercept trend/general queries FIRST
#   1. Build / update context from user input
#   2. If incomplete → ask next question + suggestions
#   3. If complete   →
#        a. Build Cortex prompt → query Snowflake Cortex
#        b. Pass Cortex leads → Insight Engine (Propensity + ICP + Persona)
#        c. Match & filter: keep only leads scored by all models
#        d. AI Validator → summary, validation note, per-lead blurbs
#        e. Return enriched result set to frontend
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter
from pydantic import BaseModel

from .context_memory      import get_context, update_context, reset_context, is_complete
from .context_builder     import build_context
from .ai_taxonomy_service import (
    get_next_field,
    generate_conversational_question,
    generate_completion_message,
    FIELD_ORDER,
)
from .intent_analyzer     import is_off_topic, generate_off_topic_reply
from .prompt_builder      import build_cortex_prompt
from .cortex_service      import query_cortex_analyst
from .insight_engine      import run_insight_engine
from .ai_validator        import validate_and_enrich
from .suggestion_engine   import get_suggestions

# ── Intent Engine ─────────────────────────────────────────────
from ..intent_engine       import route_intent

router = APIRouter(prefix="/context", tags=["Context Engine"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
 
 
class ResetRequest(BaseModel):
    session_id: str
 
 
@router.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id
    user_input = req.message.strip()
 
    state   = get_context(session_id)
    context = state["context"]
    last_suggested_geo = state.get("last_suggested_geography")
 
    # ── STEP 0: Intent Engine ─────────────────────────────────
    intent_result = route_intent(
        user_input,
        context,
        last_suggested_geography=last_suggested_geo,
    )
 
    # Geography confirmed ("yes / use India" etc.)
    if (
        intent_result.intent_type == "geography_confirmed"
        and intent_result.suggested_geography
        and not intent_result.handled
    ):
        context["geography"] = intent_result.suggested_geography
        update_context(session_id, context)
        state["last_suggested_geography"] = None
        # fall through to lead flow with geography now set
 
    # Trend or general — fully handled by intent engine
    elif intent_result.handled:
 
        payload = {
            "status":      "intent_handled",
            "intent_type": intent_result.intent_type,
            "context":     context,
            "response":    intent_result.response_text,
            "suggestions": {},
            "progress":    _progress(context),
        }
 
        # ── Rich trend payload ────────────────────────────────
        if intent_result.intent_type == "trend_query" and intent_result.trend_data:
            td = intent_result.trend_data
 
            # Filter regions to allowlist (safety net in case analyzer missed any)
            top_regions = td.top_regions[:8]
 
            # Compute average score for KPI tile
            avg_score = round(
                sum(r["score"] for r in top_regions) / len(top_regions)
            ) if top_regions else 0
 
            # Pie distribution (% of total score mass)
            total_score = sum(r["score"] for r in top_regions) or 1
            pie_slices = [
                {
                    "region": r["region"],
                    "flag":   r["flag"],
                    "score":  r["score"],
                    "pct":    round(r["score"] / total_score * 100),
                }
                for r in top_regions
            ]
 
            payload["trend_data"] = {
                # Meta
                "product":       td.product,
                "raw_available": td.raw_available,
                "data_source":   "Google Trends (live)" if td.raw_available else "Market intelligence data",
 
                # KPI tiles
                "kpi": {
                    "top_market":       top_regions[0]["region"] if top_regions else "N/A",
                    "top_market_flag":  top_regions[0]["flag"]   if top_regions else "🌍",
                    "top_market_score": top_regions[0]["score"]  if top_regions else 0,
                    "markets_analysed": len(top_regions),
                    "avg_score":        avg_score,
                    "rising_count":     len(td.rising_regions),
                },
 
                # Bar chart + region list
                "top_regions": [
                    {
                        "region": r["region"],
                        "flag":   r["flag"],
                        "score":  r["score"],
                        "pct":    round(r["score"] / (top_regions[0]["score"] or 1) * 100),
                    }
                    for r in top_regions
                ],
 
                # Donut / pie chart
                "pie_slices": pie_slices,
 
                # Time series sparkline (may be empty if rate-limited)
                "time_trend": td.time_trend,
 
                # Rising signals chips
                "rising": [
                    {"query": r["query"], "value": r["value"]}
                    for r in td.rising_regions[:6]
                ],
 
                # AI narrative
                "summary":        td.summary,
                "recommendation": td.recommendation,
 
                # CTA buttons for frontend — clicking any should POST back
                # with the geography pre-filled and continue lead flow
                "cta_geographies": [
                    {"label": f"Target {r['region']}", "geography": r["region"]}
                    for r in top_regions[:3]
                ],
            }
 
            # Store suggested geography for next-turn "yes" detection
            if top_regions:
                state["last_suggested_geography"] = top_regions[0]["region"]
                payload["trend_suggestion"] = {
                    "geography": top_regions[0]["region"],
                    "message": (
                        f"Want me to find B2B leads in {top_regions[0]['region']} "
                        f"for your {td.product} campaign? Just say yes."
                    ),
                }
 
        return payload
 
    # Lead query — clear pending suggestion
    else:
        state["last_suggested_geography"] = None
 
    # ── STEP 1: Extract context ───────────────────────────────
    context = build_context(user_input, context)
    update_context(session_id, context)
    print(f"[Session={session_id}] Context: {context}")
 
    # ── STEP 2: Check missing fields ─────────────────────────
    next_field = get_next_field(context)
 
    if next_field and is_off_topic(user_input):
        from .ai_taxonomy_service import QUESTION_MAP
        reply       = generate_off_topic_reply(user_input, context, QUESTION_MAP.get(next_field, ""))
        suggestions = get_suggestions(context, next_field)
        return {
            "status":      "in_progress",
            "context":     context,
            "response":    reply,
            "suggestions": suggestions,
            "next_field":  next_field,
            "off_topic":   True,
            "progress":    _progress(context),
        }
 
    if next_field:
        response    = generate_conversational_question(context, user_input, next_field)
        suggestions = get_suggestions(context, next_field)
        return {
            "status":      "in_progress",
            "context":     context,
            "response":    response,
            "suggestions": suggestions,
            "next_field":  next_field,
            "progress":    _progress(context),
        }
 
    # ── STEP 3: All context collected — full pipeline ─────────
    summary_msg = generate_completion_message(context)
 
    cortex_prompt = build_cortex_prompt(context, user_input)
    try:
        cortex_leads = query_cortex_analyst(cortex_prompt)
        print(f"[Cortex] {len(cortex_leads)} leads")
    except Exception as e:
        print(f"[Cortex Error] {e}")
        cortex_leads = []
 
    if not cortex_leads:
        return {
            "status":     "complete",
            "context":    context,
            "summary":    summary_msg,
            "response":   "No leads found for this criteria. Try broadening your filters.",
            "leads":      [],
            "validation": {"valid": False, "notes": "No leads returned from Cortex."},
            "suggestions": {},
        }
 
    try:
        scored_leads = run_insight_engine(cortex_leads)
    except Exception as e:
        print(f"[InsightEngine Error] {e}")
        scored_leads = []
 
    if not scored_leads:
        return {
            "status":     "complete",
            "context":    context,
            "summary":    summary_msg,
            "response":   "Leads found but none scored above the quality threshold.",
            "leads":      [],
            "validation": {"valid": False, "notes": "No leads cleared the quality threshold."},
            "suggestions": {},
        }
 
    try:
        enriched = validate_and_enrich(context, scored_leads)
    except Exception as e:
        print(f"[AIValidator Error] {e}")
        enriched = {"summary": summary_msg, "validation": {"valid": True, "notes": ""}, "leads": scored_leads}
 
    return {
        "status":     "complete",
        "context":    context,
        "summary":    enriched.get("summary", summary_msg),
        "validation": enriched.get("validation", {}),
        "leads":      enriched.get("leads", []),
        "suggestions": {},
        "progress":   {"filled": 7, "total": 7, "percent": 100},
    }
 
 
@router.post("/reset")
def reset(req: ResetRequest):
    reset_context(req.session_id)
    return {"status": "reset", "session_id": req.session_id}
 
 
@router.get("/context/{session_id}")
def get_session_context(session_id: str):
    state = get_context(session_id)
    return {
        "session_id":    session_id,
        "context":       state["context"],
        "message_count": state.get("message_count", 0),
        "complete":      is_complete(session_id),
    }
 
 
def _progress(context: dict) -> dict:
    filled = sum(1 for f in FIELD_ORDER if context.get(f))
    total  = len(FIELD_ORDER)
    return {"filled": filled, "total": total, "percent": round(filled / total * 100)}