# intent_analyzer.py
import json
from .openai_service import ask_gpt

FIELDS = [
    "geography",
    "industry",
    "industry_domain",
    "job_function",
    "job_level",
    "employee_size",
    "revenue_range"
]

# ── Product fields that contain money/budget answers ─────────────────────────
# analyze_intent() must NEVER map answers to these questions into revenue_range.
# We gate the targeting extractor so it only runs when we're in targeting phase
# or the user has clearly volunteered targeting info.
PRODUCT_MONEY_FIELDS = {"campaign_budget", "product_pricing_tier"}


def analyze_intent(user_input: str, current_phase: str = "targeting") -> dict:
    """
    Use GPT to extract structured B2B targeting context from free-form user input.
    Returns a dict with only non-empty fields populated.

    STRICT RULE: Only extract values that are EXPLICITLY stated by the user.
    Never infer or imply values.

    NEW: current_phase guard — if we're in the product phase AND the message
    looks like a budget/pricing answer, skip revenue_range extraction entirely
    to prevent "$30K budget" → revenue_range = "$25M-$49M" contamination.
    """
    # ── Budget-answer guard ───────────────────────────────────────────────────
    # If we're still collecting product fields and the input looks like a
    # budget/pricing answer, don't run the targeting extractor at all.
    # A short dollar amount with K/M suffix in the product phase is almost
    # certainly campaign_budget or pricing_tier, never a lead revenue range.
    if current_phase == "product":
        import re
        budget_pattern = re.compile(
            r"""
            \$[\d,]+[KkMmBb]?   # $30K  $500  $1.2M
            | [\d,]+[KkMmBb]\s  # 30K   500K  1M
            | budget            # the word "budget"
            | pricing
            | tier
            """,
            re.VERBOSE | re.IGNORECASE
        )
        if budget_pattern.search(user_input):
            # Almost certainly a product-phase answer — skip to avoid leaking
            # into revenue_range.
            return {}

    prompt = f"""You are a precise data extraction engine for a B2B lead targeting system.

Extract ONLY values that are EXPLICITLY and DIRECTLY stated in the user input.

STRICT RULES — violating these causes serious errors:
- NEVER infer, guess, or imply a value. If the user did not say it word-for-word (or near word-for-word), leave it as "".
- The word "campaign" does NOT imply job_function. Leave job_function as "" unless the user says e.g. "targeting Marketing" or "Sales department".
- "mid-size" or "mid-sized" maps to employee_size. Do NOT map it to revenue_range.
- "tech" or "technology" maps to industry. Do NOT also fill industry_domain unless explicitly stated.
- geography: ONLY if a country, region, or continent is explicitly named (e.g. "US", "USA", "United States", "Europe", "India")
- industry: ONLY if an industry is explicitly named (e.g. "tech", "healthcare", "finance")
- industry_domain: ONLY if a specific sub-sector is explicitly named (e.g. "SaaS", "banking", "retail")
- job_function: ONLY if a department or function is explicitly named (e.g. "Sales", "Marketing", "Engineering", "HR")
- job_level: ONLY if a seniority level is explicitly named (e.g. "C-Level", "CEO", "VP", "Director", "Manager")
- employee_size: ONLY if company size is explicitly stated (e.g. "mid-size", "enterprise", "50-249 employees", "large")
- revenue_range: ONLY if the COMPANY's annual revenue is explicitly mentioned (e.g. "$50M ARR", ">$1B revenue", "mid-market companies").
  A campaign BUDGET like "$30K" or "$500" is NOT a revenue_range — leave it as "".

Return ONLY valid JSON with no explanation and no markdown fences:
{{
    "geography": "",
    "industry": "",
    "industry_domain": "",
    "job_function": "",
    "job_level": "",
    "employee_size": "",
    "revenue_range": ""
}}

User Input: {user_input}"""

    try:
        response = ask_gpt(prompt, temperature=0.0, max_tokens=300)
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        extracted = json.loads(clean)
        return {k: v for k, v in extracted.items() if v and isinstance(v, str) and v.strip()}
    except Exception as e:
        print(f"[IntentAnalyzer Error] {e}")
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# EDIT INTENT DETECTION
# ══════════════════════════════════════════════════════════════════════════════

# Maps natural-language field references → canonical field keys.
# Covers both product fields and targeting fields.
FIELD_ALIASES: dict[str, str] = {
    # Product fields
    # "product description":  "product_description",
    # "product":              "product_description",
    "product name":         "product_name",
    "name":                 "product_name",
    "usp":                  "product_usps",
    "usps":                 "product_usps",
    "unique selling":       "product_usps",
    "selling points":       "product_usps",
    "pricing":              "product_pricing_tier",
    "price":                "product_pricing_tier",
    "pricing tier":         "product_pricing_tier",
    "product positioning":  "product_pricing_tier",
    "positioning":          "product_pricing_tier",
    "budget":               "campaign_budget",
    "campaign budget":      "campaign_budget",
    "ideal buyer":          "ideal_buyer",
    "buyer":                "ideal_buyer",
    "market type":          "target_market_type",
    "b2b":                  "target_market_type",
    "b2c":                  "target_market_type",
    "buyer stage":          "buyer_stage",
    "stage":                "buyer_stage",
    # Targeting fields
    "geography":            "geography",
    "location":             "geography",
    "country":              "geography",
    "region":               "geography",
    "industry":             "industry",
    "sector":               "industry_domain",
    "domain":               "industry_domain",
    "job function":         "job_function",
    "function":             "job_function",
    "department":           "job_function",
    "job level":            "job_level",
    "seniority":            "job_level",
    "level":                "job_level",
    "company size":         "employee_size",
    "employee size":        "employee_size",
    "employees":            "employee_size",
    "revenue":              "revenue_range",
    "revenue range":        "revenue_range",
}

# Trigger phrases that indicate an edit request
_EDIT_TRIGGERS = (
    "change", "update", "edit", "modify", "correct", "fix",
    "i want to change", "i want to update", "i want to edit",
    "switch", "replace", "set", "actually",
)


def detect_edit_intent(user_input: str) -> str | None:
    """
    Detect if the user wants to change a previously collected field.

    Returns the canonical field key (e.g. "product_pricing_tier") if an edit
    intent is detected, or None if this is a normal conversational message.

    Strategy:
      1. Fast keyword scan — if no edit trigger word is present, return None.
      2. Match field aliases in the message (longest match wins).
      3. If still ambiguous, ask GPT to resolve.
    """
    lower = user_input.lower()

    # Step 1: Check for edit trigger word
    has_trigger = any(trigger in lower for trigger in _EDIT_TRIGGERS)
    if not has_trigger:
        return None

    # Step 2: Alias matching (longest match first to avoid "level" eating "job level")
    matched_field = None
    matched_len = 0
    for alias, field in FIELD_ALIASES.items():
        if alias in lower and len(alias) > matched_len:
            matched_field = field
            matched_len = len(alias)

    if matched_field:
        return matched_field

    # Step 3: GPT fallback for ambiguous phrasing
    field_list = list(set(FIELD_ALIASES.values()))
    prompt = f"""You are a field-name resolver for a B2B campaign assistant.

The user wants to change one of their previously answered fields.
Available fields: {field_list}

User message: "{user_input}"

Which field are they trying to change?
Return ONLY the exact field name from the list above, or "none" if unclear.
No explanation."""

    try:
        result = ask_gpt(prompt, temperature=0.0, max_tokens=30).strip().lower()
        if result in field_list:
            return result
    except Exception as e:
        print(f"[EditDetector GPT Error] {e}")

    return None


def extract_new_value_for_field(user_input: str, field: str) -> str:
    """
    Given that the user wants to update `field`, extract the new value
    they provided in their message (if any).

    Returns the new value string, or "" if they haven't given a value yet
    (meaning we should ask them for it).
    """
    from .ai_taxonomy_service import FIELD_LABELS, PRODUCT_FIELDS
    field_label = FIELD_LABELS.get(field, field)
    is_product = field in PRODUCT_FIELDS

    if is_product:
        # Reuse the product extractor
        from .ai_taxonomy_service import extract_product_context
        result = extract_product_context(user_input, field)
        return result.get(field, "")
    else:
        # Use targeting extractor
        extracted = analyze_intent(user_input, current_phase="targeting")
        return extracted.get(field, "")


# ══════════════════════════════════════════════════════════════════════════════
# OFF-TOPIC DETECTION (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def is_off_topic(user_input: str) -> bool:
    prompt = f"""You are a B2B lead targeting assistant.

Determine if the user input is relevant to B2B lead targeting context like:
- geography, industry, sector, job function, job level, company size, revenue

Answer ONLY "yes" if relevant, "no" if completely off-topic.

User Input: {user_input}"""

    try:
        res = ask_gpt(prompt, temperature=0, max_tokens=5)
        return res.lower().strip() == "no"
    except:
        return False


def generate_off_topic_reply(user_input: str, context: dict, next_question: str) -> str:
    prompt = f"""You are Delphi, a smart B2B lead targeting assistant.

The user said something that is off-topic for lead targeting.

Current context collected so far:
{json.dumps(context, indent=2)}

Next question to ask: "{next_question}"

Write a SHORT, friendly, professional reply that:
1. Acknowledges their input briefly
2. Politely steers back to the task
3. Re-asks the next targeting question naturally

Keep it under 3 sentences. Sound human, not robotic."""

    try:
        return ask_gpt(prompt, temperature=0.7, max_tokens=150)
    except:
        return f"I appreciate your message! Let's continue building your lead filter. {next_question}"