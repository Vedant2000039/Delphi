# intent_engine/intent_router.py

from __future__ import annotations
import logging
from dataclasses import dataclass, field

from .intent_detector  import detect_intent_type, extract_product_from_query
from .trend_analyzer   import analyze_trends, TrendResult
from .response_builder import build_trend_response, build_general_response

log = logging.getLogger(__name__)


@dataclass
class IntentResponse:
    intent_type: str
    handled: bool
    response_text: str
    trend_data: TrendResult | None = None
    should_continue_lead_flow: bool = True
    suggested_geography: str | None = None
    metadata: dict = field(default_factory=dict)


_YES_PHRASES = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "go ahead",
    "let's do it", "do it", "proceed", "start", "yes please",
    "sounds good", "great", "perfect", "use it", "use that",
    "use usa", "use india", "use singapore", "use uk", "use germany",
    "use australia", "use canada", "use uae",
}

def _is_affirmation(text: str) -> bool:
    t = text.lower().strip().rstrip("!.")
    return t in _YES_PHRASES or t.startswith("use ")


def _handle_trend_query(user_input: str, context: dict) -> IntentResponse:
    product = extract_product_from_query(user_input)

    if not product:
        return IntentResponse(
            intent_type   = "trend_query",
            handled       = True,
            response_text = (
                "I can pull trend data for you — which product or category are you interested in? "
                "For example: 'laptop', 'CRM software', 'cloud security'."
            ),
            should_continue_lead_flow = False,
        )

    log.info(f"[IntentRouter] Trend query for: {product!r}")

    try:
        result = analyze_trends(product=product, context=context)
        response_text = build_trend_response(result, context=context)
        suggested_geo = result.top_regions[0]["region"] if result.top_regions else None

        return IntentResponse(
            intent_type            = "trend_query",
            handled                = True,
            response_text          = response_text,
            trend_data             = result,
            should_continue_lead_flow = True,
            suggested_geography    = suggested_geo,
            metadata = {
                "product":       product,
                "top_regions":   [r["region"] for r in result.top_regions[:5]],
                "raw_available": result.raw_available,
            },
        )
    except Exception as e:
        log.error(f"[IntentRouter] Trend analysis failed: {e}")
        return IntentResponse(
            intent_type   = "trend_query",
            handled       = True,
            response_text = (
                f"I ran into a temporary issue pulling trend data for '{product}'. "
                "Try again in a moment, or tell me which geography you'd like to target manually."
            ),
            should_continue_lead_flow = False,
        )


def _handle_general_query(user_input: str, context: dict) -> IntentResponse:
    return IntentResponse(
        intent_type            = "general_query",
        handled                = True,
        response_text          = build_general_response(user_input, context),
        should_continue_lead_flow = False,
    )


def route_intent(
    user_input: str,
    context: dict | None = None,
    last_suggested_geography: str | None = None,
) -> IntentResponse:
    if context is None:
        context = {}

    user_input = user_input.strip()
    if not user_input:
        return IntentResponse(
            intent_type   = "general_query",
            handled       = True,
            response_text = "I didn't catch that — could you rephrase?",
            should_continue_lead_flow = False,
        )

    # ── "Yes, use that geography" confirmation ─────────────────
    if last_suggested_geography and _is_affirmation(user_input):
        # Check if user said "use <specific country>" — extract it
        lower = user_input.lower().strip()
        geo = last_suggested_geography
        if lower.startswith("use "):
            candidate = user_input[4:].strip().title()
            if len(candidate) > 1:
                geo = candidate
        log.info(f"[IntentRouter] Geography confirmed: {geo!r}")
        return IntentResponse(
            intent_type            = "geography_confirmed",
            handled                = False,
            response_text          = "",
            suggested_geography    = geo,
            should_continue_lead_flow = True,
        )

    intent_type = detect_intent_type(user_input)
    log.info(f"[IntentRouter] intent={intent_type!r}  input={user_input!r}")

    if intent_type == "trend_query":
        return _handle_trend_query(user_input, context)

    if intent_type == "general_query":
        return _handle_general_query(user_input, context)

    if intent_type == "ambiguous":
        product = extract_product_from_query(user_input)
        if product:
            return _handle_trend_query(user_input, context)

    return IntentResponse(
        intent_type            = intent_type,
        handled                = False,
        response_text          = "",
        should_continue_lead_flow = True,
    )