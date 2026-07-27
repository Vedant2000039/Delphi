# taxonomy_matcher.py
import re
from difflib import get_close_matches
from .taxonomy_service import (
    get_industries,
    get_industry_domains,
    get_job_functions,
    get_job_levels,
    get_employee_sizes,
    get_revenue_ranges,
    is_valid_geography,
)
from .openai_service import ask_gpt


# Known geography aliases not in DB — map them to canonical names
GEOGRAPHY_ALIASES = {
    "us":            "USA",
    "usa":           "USA",
    "united states": "USA",
    "u.s.":          "USA",
    "u.s.a.":        "USA",
    "uk":            "United Kingdom",
    "u.k.":          "United Kingdom",
    "uae":           "UAE",
    "u.a.e.":        "UAE",
    "eu":            "Europe",
}


def _resolve_geography(user_input: str) -> str | None:
    """
    Resolve geography from user input.
    Checks alias map first (handles short codes like US/UK),
    then falls back to DB validation.
    """
    text = user_input.lower().strip()

    # 1. Check alias map (covers short codes the DB won't have)
    if text in GEOGRAPHY_ALIASES:
        return GEOGRAPHY_ALIASES[text]

    # 2. Check if any alias is a substring of the full input
    #    e.g. "companies in the US" → "US" → "USA"
    for alias, canonical in GEOGRAPHY_ALIASES.items():
        # Only match whole-word aliases to avoid false positives
        if re.search(r'\b' + re.escape(alias) + r'\b', text):
            return canonical

    # 3. Fall back to DB validation for full country/region names
    if is_valid_geography(text):
        return user_input.strip().title()

    return None


def _fuzzy_match(user_input: str, options: list, cutoff: float = 0.5) -> str | None:
    """
    Fast fuzzy match without LLM.
    Requires minimum 4 characters to avoid false positives on short inputs.
    """
    text = user_input.lower().strip()

    # Direct substring match — only for inputs with 4+ chars
    if len(text) >= 4:
        for opt in options:
            if text in opt.lower() or opt.lower() in text:
                return opt

    # Fuzzy fallback
    matches = get_close_matches(user_input, options, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _llm_match(user_input: str, options: list, field_name: str) -> str | None:
    """
    Use LLM to match user input against a taxonomy list FOR A SPECIFIC FIELD.

    The field_name is injected into the prompt so the model knows WHAT it is
    looking for — this prevents cross-field contamination where e.g.
    "campaign" triggers job_function = "Marketing", or "tech" triggers
    job_function = "Technology".

    The model must find a DIRECT, EXPLICIT mention of a value for this
    specific field. Implied or inferred matches must return NONE.
    """
    if not options:
        return None

    # Field-specific anti-hallucination examples baked into the prompt
    FIELD_HINTS = {
        "job_function": (
            'The word "campaign" does NOT mean job_function = Marketing. '
            '"tech companies" does NOT mean job_function = Technology. '
            'Only match if the user said a department/function name directly.'
        ),
        "job_level": (
            'Only match if the user said a seniority title like "C-Level", "VP", '
            '"Director", "Manager". Do NOT infer level from industry or company size.'
        ),
        "industry": (
            'Match the industry the user explicitly named. '
            'Do NOT match a job_function value as an industry.'
        ),
        "employee_size": (
            'Match only if the user said a size like "mid-size", "enterprise", '
            '"large", "small", or a numeric range. '
            'Do NOT infer size from revenue or industry.'
        ),
        "revenue_range": (
            'Only match if the user explicitly stated a revenue figure or range. '
            '"Mid-size" refers to company size, NOT revenue.'
        ),
    }

    hint = FIELD_HINTS.get(field_name, "Only match if the user explicitly mentioned this field.")

    prompt = f"""You are a strict taxonomy matching engine for the field "{field_name}".

User Input: "{user_input}"
Field: {field_name}
Options: {options}

Important rule: {hint}

Instructions:
- Return the EXACT matching option text if the user EXPLICITLY mentioned a value for "{field_name}".
- Return NONE if the user did not directly mention a {field_name} value.
- Do NOT infer, imply, or guess.
- Return only the option text or NONE. No explanation. No quotes."""

    try:
        res = ask_gpt(prompt, temperature=0, max_tokens=50).strip().strip('"').strip("'")
        if res.upper() == "NONE" or res not in options:
            return None
        return res
    except:
        return None


def match_taxonomy_value(user_input: str) -> dict:
    """
    Match user free-form input against all taxonomy fields.
    Returns a dict of matched field → value pairs.

    Each field is matched independently against its own taxonomy list.
    Geography is resolved via alias map + DB — never via fuzzy/LLM against
    other taxonomy lists (which causes cross-field contamination).
    """
    data = {}

    # --- GEOGRAPHY (alias map + DB — completely separate from other fields) ---
    geo = _resolve_geography(user_input)
    if geo:
        data["geography"] = geo

    # --- INDUSTRY ---
    industries = get_industries()
    match = _fuzzy_match(user_input, industries) or _llm_match(user_input, industries, "industry")
    if match:
        data["industry"] = match

    # --- INDUSTRY DOMAIN ---
    domains = get_industry_domains()
    match = _fuzzy_match(user_input, domains) or _llm_match(user_input, domains, "industry_domain")
    if match:
        data["industry_domain"] = match

    # --- JOB FUNCTION ---
    functions = get_job_functions()
    match = _fuzzy_match(user_input, functions) or _llm_match(user_input, functions, "job_function")
    if match:
        data["job_function"] = match

    # --- JOB LEVEL ---
    levels = get_job_levels()
    match = _fuzzy_match(user_input, levels) or _llm_match(user_input, levels, "job_level")
    if match:
        data["job_level"] = match

    # --- EMPLOYEE SIZE ---
    # Higher cutoff for fuzzy — size ranges look similar (e.g. "50-249" vs "250-999")
    sizes = get_employee_sizes()
    match = (
        _fuzzy_match(user_input, sizes, cutoff=0.8)
        or _llm_match(user_input, sizes, "employee_size")
    )
    if match:
        data["employee_size"] = match

    # --- REVENUE RANGE ---
    revenues = get_revenue_ranges()
    match = (
        _fuzzy_match(user_input, revenues, cutoff=0.8)
        or _llm_match(user_input, revenues, "revenue_range")
    )
    if match:
        data["revenue_range"] = match

    return data