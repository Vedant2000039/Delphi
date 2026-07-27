#new code  01052026
# ai_taxonomy_service.py
import json
from .openai_service import ask_gpt


# ══════════════════════════════════════════════════════════════
# PHASE 1 — PRODUCT & CAMPAIGN UNDERSTANDING
# Asked first, before any audience targeting questions.
# ══════════════════════════════════════════════════════════════

PRODUCT_FIELDS = [
    "product_description",   # What is your product?
    "product_name",          # What is your product name?
    "product_usps",          # Top 3 USPs
    "product_pricing_tier",  # Premium / mid-range / budget
    "campaign_budget",       # Campaign budget
    "ideal_buyer",           # Who is the ideal buyer?
    "target_market_type",    # B2B / B2C / Both
    "buyer_stage",           # First-time buyers or upgrade buyers?
]

PRODUCT_QUESTION_MAP = {
    "product_description":  "What is the product you want to run this campaign for? Describe it briefly.",
    "product_name":         "What is the name of your product?",
    "product_usps":         "What are the top 3 unique selling points (USPs) of your product?",
    "product_pricing_tier": "How would you position your product — premium, mid-range, or budget?",
    "campaign_budget":      "What is your campaign budget for this initiative?",
    "ideal_buyer":          "Who is the ideal buyer for this product? Describe them briefly.",
    "target_market_type":   "Are you targeting B2B, B2C, or both?",
    "buyer_stage":          "Are you targeting first-time buyers, upgrade buyers, or both?",
}

PRODUCT_FIELD_LABELS = {
    "product_description":  "Product Description",
    "product_name":         "Product Name",
    "product_usps":         "Product USPs",
    "product_pricing_tier": "Pricing Tier",
    "campaign_budget":      "Campaign Budget",
    "ideal_buyer":          "Ideal Buyer",
    "target_market_type":   "Target Market Type",
    "buyer_stage":          "Buyer Stage",
}


# ══════════════════════════════════════════════════════════════
# PHASE 2 — AUDIENCE TARGETING
# Classic B2B targeting fields. industry_domain is intentionally
# excluded — sector questions are not asked for now.
# ══════════════════════════════════════════════════════════════

TARGETING_FIELDS = [
    "geography",
    "industry",
    "job_function",
    "job_level",
    "employee_size",
    "revenue_range",
]

TARGETING_QUESTION_MAP = {
    "geography":    "Which geography are you targeting? (e.g. USA, Europe, India)",
    "industry":     "Which industry are you focusing on?",
    "job_function": "Which department or job function are you targeting?",
    "job_level":    "What seniority level should we focus on?",
    "employee_size":"What company size range are you targeting?",
    "revenue_range":"What annual revenue range should the companies have?",
}

TARGETING_FIELD_LABELS = {
    "geography":    "Geography",
    "industry":     "Industry",
    "job_function": "Job Function",
    "job_level":    "Seniority Level",
    "employee_size":"Company Size",
    "revenue_range":"Revenue Range",
}


# ══════════════════════════════════════════════════════════════
# COMBINED — for progress tracking and context inspection
# ══════════════════════════════════════════════════════════════

FIELD_ORDER = PRODUCT_FIELDS + TARGETING_FIELDS

QUESTION_MAP   = {**PRODUCT_QUESTION_MAP,   **TARGETING_QUESTION_MAP}
FIELD_LABELS   = {**PRODUCT_FIELD_LABELS,   **TARGETING_FIELD_LABELS}


# ══════════════════════════════════════════════════════════════
# NEXT FIELD LOGIC
# ══════════════════════════════════════════════════════════════

def get_conversation_phase(context: dict) -> str:
    """
    Returns 'product' if any product field is still missing,
    'targeting' if all product fields are filled but targeting is incomplete,
    'complete' if everything is filled.
    """
    for field in PRODUCT_FIELDS:
        if not context.get(field):
            return "product"
    for field in TARGETING_FIELDS:
        if not context.get(field):
            return "targeting"
    return "complete"


def get_next_field(context: dict) -> str | None:
    """
    Return the next required field not yet in context.
    Respects phase order: product fields first, then targeting fields.
    industry_domain is intentionally excluded from both phases.
    """
    for field in PRODUCT_FIELDS:
        if not context.get(field):
            return field
    for field in TARGETING_FIELDS:
        if not context.get(field):
            return field
    return None


def generate_next_question(context: dict) -> str | None:
    """Return the static question for the next missing field."""
    field = get_next_field(context)
    return QUESTION_MAP.get(field) if field else None


# ══════════════════════════════════════════════════════════════
# CONVERSATIONAL QUESTION GENERATION
# ══════════════════════════════════════════════════════════════

def generate_conversational_question(
    context: dict,
    user_input: str,
    next_field: str
) -> str:
    """
    Generate a context-aware, conversational question using GPT.
    Falls back to static question if GPT fails.
    Knows which phase it's in so it can set the right tone.
    """
    filled = {k: v for k, v in context.items() if v}
    base_question = QUESTION_MAP.get(next_field, "")
    field_label   = FIELD_LABELS.get(next_field, next_field)
    phase         = get_conversation_phase(context)

    phase_context = (
        "You are in the PRODUCT UNDERSTANDING phase — helping the user describe "
        "their product and campaign goals before asking about their target audience."
        if phase == "product"
        else
        "You are in the AUDIENCE TARGETING phase — collecting B2B audience filters "
        "like geography, industry, job function, seniority, company size, and revenue."
    )

    prompt = f"""You are Delphi, a smart B2B campaign and lead targeting assistant.

{phase_context}

Context collected so far:
{json.dumps(filled, indent=2)}

User's last message: "{user_input}"

Now ask about: {field_label}
Base question to ask: "{base_question}"

Write ONE short, conversational question (1-2 sentences max) that:
1. Briefly acknowledges what the user just said (naturally, not mechanically)
2. Asks for the above information
3. Sounds like a sharp consultant, not a form or chatbot

Rules:
- Do NOT use filler like "Great!", "Awesome!", "Perfect!", "Certainly!"
- Do NOT use bullet points
- Do NOT ask about anything other than the one field listed above
- Be direct and warm"""

    try:
        reply = ask_gpt(prompt, temperature=0.6, max_tokens=120)
        return reply if reply else base_question
    except Exception:
        return base_question


# ══════════════════════════════════════════════════════════════
# PRODUCT CONTEXT EXTRACTION (from free-form input)
# ══════════════════════════════════════════════════════════════

def extract_product_context(user_input: str, next_field: str) -> dict:
    """
    For product-phase fields, extract the user's answer for the specific
    field being asked. Returns {field: value} or {} if extraction fails.

    This is simpler than the targeting extraction — we just need to
    capture what the user said for the field we asked about.
    """
    prompt = f"""You are a data extraction engine for a B2B campaign planning system.

The assistant just asked the user about: "{FIELD_LABELS.get(next_field, next_field)}"
The user replied: "{user_input}"

Extract the user's answer for the field "{next_field}".

Rules:
- Return ONLY valid JSON: {{"{next_field}": "extracted value"}}
- If the user clearly answered, capture their answer as a clean string.
- For "product_usps", join the points into a single comma-separated string.
- For "target_market_type", normalise to one of: "B2B", "B2C", "B2B and B2C"
- For "product_pricing_tier", normalise to one of: "Premium", "Mid-range", "Budget"
- For "buyer_stage", normalise to one of: "First-time buyers", "Upgrade buyers", "Both"
- If the user's answer is unclear or off-topic, return {{"{next_field}": ""}}
- No explanation, no markdown."""

    try:
        response = ask_gpt(prompt, temperature=0.0, max_tokens=150)
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        extracted = json.loads(clean)
        val = extracted.get(next_field, "")
        return {next_field: val} if val and str(val).strip() else {}
    except Exception as e:
        print(f"[ProductExtractor Error] field={next_field}, error={e}")
        return {}


# ══════════════════════════════════════════════════════════════
# COMPLETION MESSAGE
# ══════════════════════════════════════════════════════════════

def generate_completion_message(context: dict) -> str:
    """
    Generate a summary message when all context (product + targeting) is collected.
    """
    prompt = f"""You are Delphi, a B2B campaign and lead targeting assistant.

The user has provided all required product and targeting context:
{json.dumps(context, indent=2)}

Write a SHORT confirmation message (2-3 sentences) that:
1. Confirms you have everything you need
2. Briefly mentions the product and the target audience in plain English
3. Says you are now finding the best matching leads

Be direct and professional. No fluff. No filler phrases."""

    try:
        return ask_gpt(prompt, temperature=0.5, max_tokens=180)
    except Exception:
        return "I have everything I need. Finding the best matching leads for your campaign now..."