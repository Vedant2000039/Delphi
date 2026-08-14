import json
import time

from openai import OpenAI

try:
    from config import OPENAI_API_KEY
except ImportError:
    from ..config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)

_cooldown_until = 0
COOLDOWN_SECONDS = 60
MAX_OUTPUT_TOKENS = 500


SYSTEM_PROMPT = """You are a B2B sales strategist. You are given
aggregated statistics about job levels and job functions found
within a brand's qualified lead population (never raw lead
records — only counts and percentages), along with the
employee-size and revenue-size bands those leads fall into.

Turn this into a buying-committee summary a salesperson can act
on immediately: who likely approves the budget, who champions
the deal internally, who else influences the decision, and
roughly how many people are typically involved.

Important: the input rows are TOP-N combinations, not a complete
census — treat them as a distribution, not rigid single facts.

Respond ONLY with a JSON object in exactly this shape, nothing
else, no explanations outside the JSON:

{
    "economic_buyer": "1 sentence describing the role/seniority that most likely holds budget authority, based on the highest-seniority job_level/job_function rows",
    "champion": "1 sentence describing the role most likely to advocate internally for this purchase day-to-day",
    "influencers": ["role 1", "role 2", "role 3"],
    "group_size": "short phrase, e.g. '4-6 stakeholders typically involved'",
    "why": "1-2 sentence explanation grounded in the actual stats given (mention frequency/percentage patterns, not raw leads)"
}
"""


def _build_user_message(candidates, brand_name, product_name):

    payload = {
        "brand": brand_name,
        "product": product_name,
        "buyer_group_candidates": candidates
    }

    return json.dumps(payload, default=str)


def _fallback_insight(candidates):
    """
    Deterministic, non-LLM summary — used if OpenAI is
    unavailable. Not as polished as the LLM version, but never
    empty and never exposes raw lead data.
    """

    def _top_row_for(level_keywords):
        for row in candidates:
            level = (row.get("job_level") or "").lower()
            if any(k in level for k in level_keywords):
                return row
        return None

    top_row = candidates[0] if candidates else {}

    exec_row = _top_row_for(["vp", "chief", "c-level", "president"]) or top_row
    champion_row = _top_row_for(["director", "manager"]) or top_row

    influencer_functions = list(dict.fromkeys(
        row.get("job_function") for row in candidates[1:4] if row.get("job_function")
    ))

    total_leads = sum(row.get("lead_count", 0) for row in candidates)

    return {
        "economic_buyer": (
            f"{exec_row.get('job_level', 'Senior leadership')} in "
            f"{exec_row.get('job_function', 'the relevant function')} "
            f"typically holds budget authority."
        ),
        "champion": (
            f"{champion_row.get('job_level', 'Mid-level management')} in "
            f"{champion_row.get('job_function', 'the relevant function')} "
            f"is the most frequent day-to-day advocate."
        ),
        "influencers": influencer_functions or ["Not enough data"],
        "group_size": f"Based on {len(candidates)} distinct role patterns found",
        "why": (
            f"Based on {total_leads} qualified leads across the top "
            f"{len(candidates)} role combinations for this brand."
        )
    }


def generate_buyer_group_insight(candidates, brand_name=None, product_name=None):
    """
    Produces the human-facing buying-committee summary rendered
    by BuyerGroup.js. Never receives or exposes individual lead
    records — only aggregated stats from Usp_get_buyer_groups.
    Falls back silently to a deterministic summary if OpenAI is
    unavailable, rate-limited, or misconfigured.
    """

    global _cooldown_until

    if not OPENAI_API_KEY or time.time() < _cooldown_until:
        return _fallback_insight(candidates)

    try:
        user_message = _build_user_message(candidates, brand_name, product_name)

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=MAX_OUTPUT_TOKENS,
            timeout=15
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        required = ["economic_buyer", "champion", "influencers", "group_size", "why"]

        if not all(k in parsed for k in required):
            return _fallback_insight(candidates)

        return parsed

    except Exception as e:

        if "429" in str(e) or "rate limit" in str(e).lower():
            _cooldown_until = time.time() + COOLDOWN_SECONDS

        return _fallback_insight(candidates)