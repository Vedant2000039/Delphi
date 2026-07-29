# intent_engine/response_builder.py

from __future__ import annotations
import json
import logging
import os
import sys

log = logging.getLogger(__name__)


def _get_ask_gpt():
    # 1. Relative import
    try:
        from ..openai_service import ask_gpt
        return ask_gpt
    except (ImportError, ValueError):
        pass
    # 2. Walk up directory tree
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        for path in [os.path.dirname(here), os.path.dirname(os.path.dirname(here))]:
            if path not in sys.path:
                sys.path.insert(0, path)
        from openai_service import ask_gpt
        return ask_gpt
    except ImportError:
        pass
    # 3. Direct OpenAI client
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        def ask_gpt(prompt, temperature=0.7, max_tokens=500):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        return ask_gpt
    except Exception as e:
        log.error(f"[ResponseBuilder] Cannot load ask_gpt: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# FIELD BRIDGE — determines what to ask next in lead flow
# ─────────────────────────────────────────────────────────────

FIELD_ORDER = ["geography", "industry", "job_function", "job_level", "employee_size", "revenue_range"]

FIELD_BRIDGE = {
    "geography":     lambda top1, top2, product: (
        f"Would you like to use **{top1}**{f' or **{top2}**' if top2 else ''} as your target geography "
        f"for the {product} campaign? Just say yes and I'll start pulling leads there."
    ),
    "industry":      lambda *_: "Which industry are you targeting? (e.g. Technology, Healthcare, Financial Services)",
    "job_function":  lambda *_: "Which department or job function do you want to reach? (e.g. Sales, Engineering, Marketing)",
    "job_level":     lambda *_: "What seniority level are you targeting? (e.g. C-Level, VP, Director, Manager)",
    "employee_size": lambda *_: "What company size range should we focus on? (e.g. 50–200, 1000+)",
    "revenue_range": lambda *_: "What annual revenue range should the target companies have?",
}


def _get_bridge(context: dict, top1: str, top2: str, product: str) -> str:
    missing = [f for f in FIELD_ORDER if not context.get(f)]
    if not missing:
        return "I have everything I need — ready to find leads whenever you are."
    fn = FIELD_BRIDGE.get(missing[0])
    return fn(top1, top2, product) if fn else "What would you like to do next?"


# ─────────────────────────────────────────────────────────────
# MAIN: TREND RESPONSE
# ─────────────────────────────────────────────────────────────

def build_trend_response(result, context: dict | None = None) -> str:
    """
    Returns a clean conversational string.
    The heavy analytics (charts, KPI tiles) are rendered by the frontend
    using the structured trend_data payload from routes.py.
    This text sits ABOVE the visual card as the chat message.
    """
    if context is None:
        context = {}

    ask_gpt = _get_ask_gpt()

    top1 = result.top_regions[0]["region"] if result.top_regions else "the United States"
    top2 = result.top_regions[1]["region"] if len(result.top_regions) > 1 else ""

    bridge = _get_bridge(context, top1, top2, result.product)

    region_lines = "\n".join(
        f"  {i}. {r['flag']} {r['region']} — {r['score']}/100"
        for i, r in enumerate(result.top_regions[:6], 1)
    )

    rising_str = ", ".join(
        f"{r['query']} ({r['value']})" for r in result.rising_regions[:4]
    ) if result.rising_regions else "none detected"

    data_source = "live Google Trends data" if result.raw_available else "market intelligence benchmarks"

    if ask_gpt is None:
        return _fallback_response(result, bridge)

    prompt = f"""You are Delphi, a sharp B2B market intelligence assistant.

You just pulled {data_source} for: "{result.product}"

Noise-filtered top regions:
{region_lines}

Rising searches: {rising_str}
Pre-computed summary: {result.summary}
Pre-computed recommendation: {result.recommendation}

Write a SHORT conversational response (max 200 words) split into exactly 3 parts:

PART 1 — Market read (2 sentences max):
Give the sharpest possible insight about what this data means for someone selling {result.product} B2B. Name the top 2 markets explicitly. Be direct, not generic.

PART 2 — Region highlights (4-5 bullet points):
For each top region use this exact format:
• [flag] **Country** — one-line B2B-specific comment (e.g. market maturity, buyer density, adoption stage)

PART 3 — Bridge (1 sentence):
Exactly this text, word for word: {bridge}

Rules:
- No headers, no markdown title blocks
- No filler openers ("Great!", "Sure!", "Certainly!")
- Bullet points use • not - or *
- Bold only country names in bullets
- Part 3 must be the EXACT bridge text provided above, unchanged"""

    try:
        response = ask_gpt(prompt, temperature=0.55, max_tokens=400)
        if response and len(response) > 80:
            log.info(f"[ResponseBuilder] GPT success ({len(response)} chars)")
            return response
        log.warning(f"[ResponseBuilder] GPT short response: {response!r}")
        return _fallback_response(result, bridge)
    except Exception as e:
        log.error(f"[ResponseBuilder] GPT failed: {e}")
        return _fallback_response(result, bridge)


def _fallback_response(result, bridge: str) -> str:
    lines = [f"Here's what the trend data shows for **{result.product}**:\n"]
    for i, r in enumerate(result.top_regions[:6], 1):
        lines.append(f"• {r['flag']} **{r['region']}** — {r['score']}/100")
    if result.summary:
        lines.append(f"\n{result.summary}")
    lines.append(f"\n{bridge}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# GENERAL / OFF-TOPIC
# ─────────────────────────────────────────────────────────────

def build_general_response(user_input: str, context: dict) -> str:
    ask_gpt = _get_ask_gpt()

    missing = [f for f in FIELD_ORDER if not context.get(f)]
    filled  = {k: v for k, v in context.items() if v}

    field_map = {
        "geography":     "which geography or country they want to target",
        "industry":      "which industry they're targeting",
        "job_function":  "which department or job function to reach",
        "job_level":     "what seniority level they're targeting",
        "employee_size": "what company size range to focus on",
        "revenue_range": "what annual revenue range the companies should have",
    }

    next_q   = missing[0] if missing else None
    ctx_note = f"Collected so far: {json.dumps(filled)}." if filled else "No context yet."
    steer    = f"ask about {field_map[next_q]}" if next_q else "say you're ready to find leads"

    if not ask_gpt:
        return (
            "That's outside my focus — I'm built for B2B lead intelligence. "
            + (f"What {missing[0].replace('_',' ')} are you targeting?" if missing else "Ready to find leads!")
        )

    prompt = f"""You are Delphi, a B2B lead intelligence assistant.

User said something off-topic: "{user_input}"
{ctx_note}

Write 1-2 sentences: acknowledge you can't help with that, then {steer}.
No filler phrases. Be warm but brief."""

    try:
        return ask_gpt(prompt, temperature=0.6, max_tokens=80)
    except Exception:
        return "That's outside my lane — I'm focused on B2B lead intelligence. What are you targeting?"