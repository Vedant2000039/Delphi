# apis/p3_campaign/p3_paths.py
from __future__ import annotations
import re
import json
from apis.context_engine.openai_service  import ask_gpt
from apis.context_engine.intent_analyzer import analyze_intent
from apis.context_engine.taxonomy_matcher import match_taxonomy_value

# Keyword signals that the user is accepting/selecting a shown campaign
_ACCEPT_KEYWORDS = (
    "go with", "select", "pick", "choose", "option",
    "campaign", "number", "first", "second", "third",
    "fourth", "fifth", "1st", "2nd", "3rd", "4th", "5th",
    "1", "2", "3", "4", "5",
    "that one", "this one", "looks good", "perfect",
    "sounds good", "yes", "yeah", "go ahead",
)
# Keyword signals that the user wants to change/adjust something
_MODIFY_KEYWORDS = (
    "but", "except", "change", "instead", "modify",
    "adjust", "update", "different", "not exactly",
    "tweak", "however", "although", "modification",
    "modifications", "want changes", "slight change",
)
# Keyword signals that the user is declining all shown campaigns
_REJECT_KEYWORDS = (
    "no", "none", "skip", "reject", "fresh start",
    "start fresh", "start over", "define my own",
    "my own criteria", "something different",
    "not interested", "don't like", "don't want",
    "nope", "neither",
)
# Maps ordinal words/digits to their zero-based campaign index
_ORDINALS = {
    "first": 0, "1st": 0, "one": 0, "1": 0,
    "second": 1, "2nd": 1, "two": 1, "2": 1,
    "third": 2, "3rd": 2, "three": 2, "3": 2,
    "fourth": 3, "4th": 3, "four": 3, "4": 3,
    "fifth": 4, "5th": 4, "five": 4, "5": 4,
}


def detect_path(user_input: str, display_campaigns: list[dict]) -> str:
    """
    Classify the user's reply to the shown campaign recommendations into
    one of: "accept", "modify_campaign", "modify_free", or "reject".

    Tries fast keyword-based rules first; falls back to GPT classification
    only if none of the rules confidently match.
    """
    lower       = user_input.lower()
    has_reject  = any(kw in lower for kw in _REJECT_KEYWORDS)
    has_modify  = any(kw in lower for kw in _MODIFY_KEYWORDS)
    has_accept  = any(kw in lower for kw in _ACCEPT_KEYWORDS)
    # Word-boundary check for an ordinal reference (word or 1-5 digit)
    has_ordinal = bool(re.search(
        r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|[1-5])\b', lower
    ))

    # Pure rejection: reject language with no acceptance or campaign reference
    if has_reject and not has_accept and not has_ordinal:
        return "reject"
    # User picked a campaign (by ordinal or accept keyword) but also wants changes
    if (has_ordinal or has_accept) and has_modify:
        return "modify_campaign"
    # User picked a campaign with no modification language
    if has_ordinal or (has_accept and not has_modify):
        return "accept"
    # User wants changes but didn't reference a specific campaign
    if has_modify and not has_ordinal:
        return "modify_free"

    # None of the keyword rules matched confidently — ask GPT to classify
    return _gpt_detect_path(user_input, display_campaigns)


def _gpt_detect_path(user_input: str, display_campaigns: list[dict]) -> str:
    """GPT fallback classifier for detect_path(), used when keyword rules are inconclusive."""
    n = len(display_campaigns)
    prompt = f"""A user was shown {n} de-identified B2B campaign targeting profiles
and a targeting recommendation. They responded:

"{user_input}"

Classify their response as EXACTLY ONE of:
- "accept"          — selected a specific campaign (1–{n}), no changes
- "modify_campaign" — selected a campaign AND wants to change something
- "modify_free"     — wants modifications but didn't pick a specific campaign
- "reject"          — declined all, wants to define their own criteria

Return ONLY the classification string. No explanation."""

    try:
        # Deterministic completion; strip quotes GPT sometimes wraps the answer in
        result = ask_gpt(prompt, temperature=0.0, max_tokens=20).strip().lower().strip('"')
        if result in ("accept", "modify_campaign", "modify_free", "reject"):
            return result
    except Exception as e:
        print(f"[P3Paths] GPT path detection error: {e}")
    # Safe default if GPT fails or returns something unrecognized
    return "modify_free"


def detect_campaign_selection(user_input: str, display_campaigns: list[dict]) -> int | None:
    """
    Determine which displayed campaign (by zero-based index) the user is
    referring to. Tries, in order: an ordinal word/digit match, a direct
    substring match against a campaign's own field values, then a GPT
    fallback. Returns None if no campaign could be identified.
    """
    lower = user_input.lower()
    n     = len(display_campaigns)

    # 1. Check for an explicit ordinal reference (e.g. "the second one", "3rd")
    for word, idx in _ORDINALS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', lower):
            if idx < n:
                return idx

    # 2. Check if the user quoted one of the campaign's own field values
    #    (e.g. mentioned "Director" and only one campaign has that job_level)
    for i, c in enumerate(display_campaigns):
        for field in ("job_level", "job_function", "employee_size", "revenue_range"):
            val = (c.get(field) or "").lower()
            if val and val != "not specified" and val in lower:
                return i

    # 3. Fall back to GPT: build a numbered list of the campaigns and ask
    #    which one the user's message refers to
    numbered = "\n".join(
        f"{c['index']}. {c['job_level']} {c['job_function']} | "
        f"{c['employee_size']} | {c['revenue_range']}"
        for c in display_campaigns
    )
    prompt = f"""A user was shown these campaign profiles:

{numbered}

User said: "{user_input}"

Which campaign number (1–{n}) are they referring to?
Return ONLY the number (1–{n}), or NONE if unclear. No explanation."""

    try:
        result = ask_gpt(prompt, temperature=0.0, max_tokens=10).strip()
        if result.isdigit():
            # Prompt asks for a 1-based number; convert to zero-based index
            idx = int(result) - 1
            if 0 <= idx < n:
                return idx
    except Exception as e:
        print(f"[P3Paths] GPT campaign selection error: {e}")
    # No ordinal, field, or GPT match found
    return None


def extract_modifications(user_input: str) -> dict:
    """
    Extract any explicitly-stated targeting field changes (job_level,
    job_function, employee_size, revenue_range) from the user's message.

    Tries the existing intent/taxonomy extractors first; only falls back
    to a dedicated GPT extraction prompt if those return nothing usable.
    """
    extracted = {}
    try:
        # Run both extractors and merge their results (taxonomy_data can override intent_data)
        intent_data   = analyze_intent(user_input, current_phase="targeting")
        taxonomy_data = match_taxonomy_value(user_input)
        extracted     = {**intent_data, **taxonomy_data}
    except Exception as e:
        print(f"[P3Paths] Extractor error: {e}")

    # Keep only the targeting fields we care about, and only if they have a value
    targeting_fields = {"job_level", "job_function", "employee_size", "revenue_range"}
    extracted = {k: v for k, v in extracted.items() if k in targeting_fields and v}

    if extracted:
        # Existing extractors found something usable — no need to call GPT
        return extracted

    # GPT fallback
    prompt = f"""You are a data extraction engine for a B2B campaign tool.

Extract ONLY values explicitly stated in the user input for these fields:
- job_level     (e.g. C-Suite, VP, Director, Manager)
- job_function  (e.g. Finance, Marketing, Engineering, Operations)
- employee_size (e.g. Mid-size, Enterprise, Small business)
- revenue_range (e.g. $50M–$500M, >$1B, Mid-market)

User input: "{user_input}"

Return ONLY valid JSON. Empty string for fields not mentioned. No markdown.
{{"job_level":"","job_function":"","employee_size":"","revenue_range":""}}"""

    try:
        response = ask_gpt(prompt, temperature=0.0, max_tokens=150).strip()
        # Strip markdown code fences if GPT wrapped the JSON in ```/```json
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response.strip())
        # Drop any fields that came back empty/blank
        return {k: v for k, v in data.items() if v and str(v).strip()}
    except Exception as e:
        print(f"[P3Paths] GPT extraction error: {e}")
        return {}


def build_targeting_from_campaign(campaign: dict) -> dict:
    """Build a targeting dict seeded from a selected campaign's own field values (None if missing)."""
    return {
        "job_level":     campaign.get("job_level")     or None,
        "job_function":  campaign.get("job_function")  or None,
        "employee_size": campaign.get("employee_size") or None,
        "revenue_range": campaign.get("revenue_range") or None,
    }


def apply_overrides(base: dict, overrides: dict) -> dict:
    """Return a copy of `base` with any non-empty values from `overrides` applied on top."""
    result = {**base}
    for k, v in overrides.items():
        if v and str(v).strip():
            result[k] = v
    return result


def format_targeting_summary(
    product: str, geography: str, industry: str, targeting: dict
) -> str:
    """Render a plain-text summary of the product, geography, industry, and targeting fields."""
    lines = [
        f"Product:       {product}",
        f"Geography:     {geography}",
        f"Industry:      {industry}",
        f"Job Level:     {targeting.get('job_level')     or 'Not specified'}",
        f"Job Function:  {targeting.get('job_function')  or 'Not specified'}",
        f"Company Size:  {targeting.get('employee_size') or 'Not specified'}",
        f"Revenue Range: {targeting.get('revenue_range') or 'Not specified'}",
    ]
    return "\n".join(lines)