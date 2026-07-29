# intent_engine/intent_detector.py

from __future__ import annotations
import re
import logging
import os
import sys

log = logging.getLogger(__name__)

TREND_KEYWORDS = [
    "trend", "trending", "popular", "hotspot", "in demand",
    "growing market", "best region", "best country", "top country",
    "which country", "which region", "where is", "where should",
    "google trends", "market trend", "demand", "fastest growing",
    "emerging market", "recommend country", "recommend region",
    "target region", "where to sell", "where to launch",
]

LEAD_KEYWORDS = [
    "lead", "leads", "campaign", "targeting", "icp", "prospect",
    "contact", "company size", "revenue", "job title", "seniority",
    "industry", "geography", "filter", "find me", "show me leads",
    "get leads", "fetch leads",
]

GENERAL_KEYWORDS = [
    "weather", "joke", "tell me about", "history of",
    "meaning of", "what is the capital", "recipe",
    "movie", "song", "sport",
]

# ─────────────────────────────────────────────────────────────
# SHORT ANSWER ALLOWLIST
# These are valid one-word / short answers to lead flow questions.
# They must NEVER be classified as general_query or off-topic.
# ─────────────────────────────────────────────────────────────
SHORT_ANSWER_PATTERNS = [
    # Job levels
    r"^(c[\-\s]?level|c suite|c-suite|vp|vice president|director|manager|senior manager|"
    r"head of|executive|entry level|individual contributor|analyst|associate|partner|"
    r"president|ceo|cto|cfo|coo|cmo|ciso|founder|owner)s?$",
    # Industries
    r"^(technology|healthcare|finance|financial services|manufacturing|retail|"
    r"education|government|real estate|media|telecom|energy|pharma|"
    r"pharmaceuticals|logistics|hospitality|insurance|legal|consulting|"
    r"saas|fintech|edtech|martech|healthtech|proptech|legaltech)$",
    # Job functions
    r"^(sales|marketing|engineering|hr|human resources|operations|finance|"
    r"product|it|information technology|legal|customer success|"
    r"business development|procurement|supply chain|research|design|"
    r"data|analytics|security|devops|support)$",
    # Company sizes
    r"^(\d+[\+\-]\d*|\d+\s*to\s*\d+|\d+\s*\+|small|medium|large|enterprise|"
    r"startup|mid[\-\s]?market|smb)$",
    # Revenue ranges
    r"^(\$[\d,]+[mk]?\s*[\-\+]?\s*\$?[\d,]*[mk]?|under \$|above \$|"
    r"[\d,]+\s*million|[\d,]+\s*billion)$",
    # Geographies (short names)
    r"^(usa|uk|uae|us|eu|apac|emea|latam|india|china|germany|france|"
    r"canada|australia|singapore|brazil|japan|italy|spain|netherlands|"
    r"sweden|poland|israel|south korea|indonesia|malaysia|thailand|"
    r"vietnam|philippines|south africa|nigeria|kenya|egypt|"
    r"saudi arabia|qatar|mexico|argentina|colombia)$",
    # Affirmations (handled by router but safe to allow here too)
    r"^(yes|no|sure|ok|okay|yeah|yep|correct|exactly|right|confirmed)$",
    # "use <country>" pattern
    r"^use\s+\w[\w\s]{1,30}$",
    # Single word that is > 2 chars and not a known general keyword
    # (catches "Manager level", "Software", "50-200" etc.)
    r"^[\w\s\-\+\$]{2,40}$",  # broad catch-all for short answers
]

_SHORT_ANSWER_RE = [re.compile(p, re.IGNORECASE) for p in SHORT_ANSWER_PATTERNS]


def _is_short_field_answer(text: str) -> bool:
    """
    Returns True if the text looks like a valid short answer
    to a lead flow question (job level, industry, size, etc.).
    Short = under 6 words.
    """
    words = text.strip().split()
    if len(words) > 6:
        return False  # long sentences need full classification
    for pat in _SHORT_ANSWER_RE:
        if pat.match(text.strip()):
            return True
    return False


def _keyword_classify(text: str) -> str | None:
    lower = text.lower()
    trend_hits = sum(1 for kw in TREND_KEYWORDS if kw in lower)
    lead_hits  = sum(1 for kw in LEAD_KEYWORDS  if kw in lower)
    gen_hits   = sum(1 for kw in GENERAL_KEYWORDS if kw in lower)

    if trend_hits > 0 and lead_hits == 0:
        return "trend_query"
    if lead_hits > 0 and trend_hits == 0:
        return "lead_query"
    if trend_hits > 0 and lead_hits > 0:
        return "trend_query"
    if gen_hits > 0 and trend_hits == 0 and lead_hits == 0:
        return "general_query"
    return None


def _get_ask_gpt():
    try:
        from ..openai_service import ask_gpt
        return ask_gpt
    except (ImportError, ValueError):
        pass
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        for path in [os.path.dirname(here), os.path.dirname(os.path.dirname(here))]:
            if path not in sys.path:
                sys.path.insert(0, path)
        from openai_service import ask_gpt
        return ask_gpt
    except ImportError:
        return None


def _llm_classify(user_input: str) -> str:
    ask_gpt = _get_ask_gpt()
    if not ask_gpt:
        log.warning("[IntentDetector] ask_gpt unavailable")
        return "lead_query"  # safe default: let lead flow handle it

    prompt = f"""You are an intent classifier for Delphi, a B2B lead intelligence platform.

The platform collects targeting info step by step: geography, industry, job function, job level, company size, revenue range.
Users often reply with SHORT ANSWERS like "Manager", "Healthcare", "USA", "50-200 employees", "$10M-$100M".
These short answers are ALWAYS "lead_query".

Classify this message into exactly ONE category:
- "lead_query"    → a lead-related answer OR question (including short field answers like "Manager", "Technology", "USA", "C-Level", company sizes, revenue ranges)
- "trend_query"   → asking what is trending, which region/country has demand for a product
- "general_query" → completely off-topic (weather, jokes, cooking, unrelated questions)
- "ambiguous"     → genuinely unclear

Message: "{user_input}"

Return ONLY the category name. No explanation."""

    try:
        result = ask_gpt(prompt, temperature=0, max_tokens=10).strip().lower()
        return result if result in {"lead_query", "trend_query", "general_query", "ambiguous"} else "lead_query"
    except Exception as e:
        log.warning(f"[IntentDetector] LLM error: {e}")
        return "lead_query"  # safe default


def detect_intent_type(user_input: str) -> str:
    """
    Returns: "lead_query" | "trend_query" | "general_query" | "ambiguous"
    """
    # Short field answers are ALWAYS lead_query — check first, no LLM needed
    if _is_short_field_answer(user_input):
        log.debug(f"[IntentDetector] short_answer → lead_query: {user_input!r}")
        return "lead_query"

    fast = _keyword_classify(user_input)
    if fast:
        log.debug(f"[IntentDetector] keyword → {fast}")
        return fast

    result = _llm_classify(user_input)
    log.debug(f"[IntentDetector] llm → {result}")
    return result


def extract_product_from_query(user_input: str) -> str | None:
    ask_gpt = _get_ask_gpt()

    if ask_gpt:
        prompt = f"""Extract the PRODUCT or CATEGORY the user wants trend data for.

Input: "{user_input}"

Rules:
- Return ONLY the product/category name (e.g. "laptop", "CRM software", "cloud security", "healthcare")
- Return NONE if no specific product is mentioned
- Do not return verbs or generic words like "trend" or "market"

Examples:
"which country is laptop trending?" → laptop
"trending regions for healthcare?" → healthcare
"where should I sell my ERP software?" → ERP software
"what's popular?" → NONE
"trend for kawasaki" → kawasaki
"Manager" → NONE
"C-Level" → NONE
"50-200" → NONE"""

        try:
            result = ask_gpt(prompt, temperature=0, max_tokens=20).strip()
            if result.upper() != "NONE" and len(result) > 1:
                return result
        except Exception:
            pass

    # Regex fallback
    patterns = [
        r"trend(?:ing)?\s+(?:for|in|of)\s+([a-zA-Z0-9][a-zA-Z0-9 \-]{1,30}?)(?:\?|$|\s+in\s)",
        r"(?:for|about|selling)\s+(?:my\s+)?([a-zA-Z0-9][a-zA-Z0-9 \-]{1,30}?)\s+(?:product|software|campaign|leads)",
        r"([a-zA-Z0-9][a-zA-Z0-9 \-]{1,20}?)\s+(?:is\s+)?trending",
    ]
    for pat in patterns:
        m = re.search(pat, user_input, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate.lower() not in {"the", "a", "an", "my", "your", "this"}:
                return candidate
    return None