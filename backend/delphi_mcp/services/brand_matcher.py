# # import json
# # import time

# # from openai import OpenAI

# # from config import OPENAI_API_KEY


# # client = OpenAI(api_key=OPENAI_API_KEY)


# # # ----------------------------------------------------------
# # # In-memory cache: product string -> brand name list
# # # (avoids repeat OpenAI calls for the same product within
# # # a running server process)
# # # ----------------------------------------------------------
# # _cache = {}

# # # ----------------------------------------------------------
# # # Cooldown state for 429 handling, mirroring the pattern
# # # already used in openai_service.py
# # # ----------------------------------------------------------
# # _cooldown_until = 0
# # COOLDOWN_SECONDS = 60

# # # Fallback map used if OpenAI is unavailable, misconfigured,
# # # rate-limited, or returns something unusable.
# # FALLBACK_MAPPING = {
# #     "macbook": ["Dell", "HP", "Lenovo"],
# #     "iphone": ["Samsung", "Google Pixel"],
# #     "windows": ["Dell", "HP"],
# # }


# # SYSTEM_PROMPT = """You are a B2B market analyst.
# # Given a product name, return the closest competing brands —
# # companies that make directly comparable products.

# # Rules:
# # - Return ONLY real, well-known company/brand names.
# # - 3 to 8 brands, most relevant first.
# # - No explanations, no extra text.
# # - Respond ONLY in this exact JSON format, nothing else:

# # {"brands": ["Brand1", "Brand2", "Brand3"]}
# # """


# # def _call_openai(product):

# #     response = client.chat.completions.create(
# #         model="gpt-4.1",
# #         messages=[
# #             {"role": "system", "content": SYSTEM_PROMPT},
# #             {"role": "user", "content": f"Product: {product}"}
# #         ],
# #         temperature=0,
# #         response_format={"type": "json_object"},
# #         timeout=10
# #     )

# #     raw = response.choices[0].message.content

# #     parsed = json.loads(raw)

# #     brands = parsed.get("brands", [])

# #     # Guard against garbage: must be a list of non-empty strings
# #     if not isinstance(brands, list):
# #         return []

# #     cleaned = [
# #         b.strip()
# #         for b in brands
# #         if isinstance(b, str) and b.strip()
# #     ]

# #     return cleaned


# # def find_similar_brands_llm(product):
# #     """
# #     Returns a list of brand names similar/competing to the
# #     given product, using OpenAI. Falls back silently to the
# #     hardcoded mapping (or an empty list) on any failure —
# #     this matches the existing resilience pattern used
# #     elsewhere in the codebase (openai_service.py).
# #     """

# #     global _cooldown_until

# #     if not product:
# #         return []

# #     key = product.lower().strip()

# #     # ---- Cache hit ----
# #     if key in _cache:
# #         return _cache[key]

# #     # ---- No API key configured: skip straight to fallback ----
# #     if not OPENAI_API_KEY:
# #         return FALLBACK_MAPPING.get(key, [])

# #     # ---- Cooldown active from a recent 429 ----
# #     if time.time() < _cooldown_until:
# #         return FALLBACK_MAPPING.get(key, [])

# #     try:
# #         brands = _call_openai(product)

# #         if not brands:
# #             # Empty/garbage response — fall back rather than
# #             # returning nothing when we have a known mapping.
# #             return FALLBACK_MAPPING.get(key, [])

# #         _cache[key] = brands

# #         return brands

# #     except Exception as e:

# #         # Handle rate limits with a cooldown so we don't
# #         # hammer OpenAI on every subsequent request.
# #         if "429" in str(e) or "rate limit" in str(e).lower():
# #             _cooldown_until = time.time() + COOLDOWN_SECONDS

# #         # Any failure (timeout, bad JSON, network, auth) —
# #         # degrade silently to the hardcoded mapping.
# #         return FALLBACK_MAPPING.get(key, [])


# import json
# import time

# from openai import OpenAI

# from config import OPENAI_API_KEY


# client = OpenAI(api_key=OPENAI_API_KEY)


# # ----------------------------------------------------------
# # In-memory cache: product string -> full analysis dict
# # (avoids repeat OpenAI calls for the same product within
# # a running server process)
# # ----------------------------------------------------------
# _cache = {}

# # ----------------------------------------------------------
# # Cooldown state for 429 handling, mirroring the pattern
# # already used in openai_service.py
# # ----------------------------------------------------------
# _cooldown_until = 0
# COOLDOWN_SECONDS = 60

# # Hard cap on response size — the schema is small and bounded,
# # so this is a safety net against a runaway/misbehaving response,
# # not a normal operating limit.
# MAX_OUTPUT_TOKENS = 400

# # Fallback data used if OpenAI is unavailable, misconfigured,
# # rate-limited, or returns something unusable. Kept intentionally
# # small — only for the products we already knew about before the
# # LLM existed. Anything not in here falls back to a generic
# # "unknown product" shape rather than returning nulls.
# FALLBACK_ANALYSIS = {
#     "macbook": {
#         "product_type": "Laptop",
#         "category": "Computers",
#         "industry": "Consumer Electronics",
#         "technology": ["Personal Computing"],
#         "manufacturer": "Apple",
#         "competitor_brands": ["Dell", "HP", "Lenovo"],
#         "keywords": ["Laptop", "Notebook", "Portable Computer"],
#     },
#     "iphone": {
#         "product_type": "Smartphone",
#         "category": "Mobile Devices",
#         "industry": "Consumer Electronics",
#         "technology": ["Mobile Computing"],
#         "manufacturer": "Apple",
#         "competitor_brands": ["Samsung", "Google Pixel"],
#         "keywords": ["Smartphone", "Mobile Phone"],
#     },
#     "windows": {
#         "product_type": "Operating System",
#         "category": "Software",
#         "industry": "Enterprise Software",
#         "technology": ["Operating Systems"],
#         "manufacturer": "Microsoft",
#         "competitor_brands": ["Dell", "HP"],
#         "keywords": ["Operating System", "OS"],
#     },
# }

# REQUIRED_KEYS = [
#     "product_type",
#     "category",
#     "industry",
#     "technology",
#     "manufacturer",
#     "competitor_brands",
#     "keywords",
# ]


# SYSTEM_PROMPT = """You are a B2B market analyst.
# Given a product, technology, or service name, analyze it
# completely so it can be matched against a CRM of companies
# and their brands.

# Even if the input is vague, unusual, or not a well-known
# product, make your best reasonable inference — never return
# empty or null fields. Use general category knowledge if you
# don't recognize the specific name.

# Respond ONLY with a JSON object in exactly this shape,
# nothing else, no explanations:

# {
#     "product_type": "short type label, e.g. Laptop",
#     "category": "broader category, e.g. Computers",
#     "industry": "industry this belongs to, e.g. Consumer Electronics",
#     "technology": ["relevant technology areas"],
#     "manufacturer": "known manufacturer, or best guess, or 'Unknown'",
#     "competitor_brands": ["3 to 8 real, well-known competing brand names, most relevant first"],
#     "keywords": ["3 to 6 related search keywords"]
# }
# """


# def _validate_and_clean(parsed):

#     if not isinstance(parsed, dict):
#         return None

#     for key in REQUIRED_KEYS:
#         if key not in parsed:
#             return None

#     def _clean_list(value):
#         if not isinstance(value, list):
#             return []
#         return [
#             v.strip()
#             for v in value
#             if isinstance(v, str) and v.strip()
#         ]

#     cleaned = {
#         "product_type": str(parsed.get("product_type") or "Unknown").strip(),
#         "category": str(parsed.get("category") or "Unknown").strip(),
#         "industry": str(parsed.get("industry") or "Unknown").strip(),
#         "technology": _clean_list(parsed.get("technology")),
#         "manufacturer": str(parsed.get("manufacturer") or "Unknown").strip(),
#         "competitor_brands": _clean_list(parsed.get("competitor_brands")),
#         "keywords": _clean_list(parsed.get("keywords")),
#     }

#     return cleaned


# def _call_openai(product):

#     response = client.chat.completions.create(
#         model="gpt-4.1",
#         messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": f"Product: {product}"}
#         ],
#         temperature=0,
#         response_format={"type": "json_object"},
#         max_tokens=MAX_OUTPUT_TOKENS,
#         timeout=10
#     )

#     raw = response.choices[0].message.content

#     parsed = json.loads(raw)

#     return _validate_and_clean(parsed)


# def _generic_fallback(product):
#     """
#     Used when the product isn't in FALLBACK_ANALYSIS and OpenAI
#     is unavailable. Keeps the schema fully populated (no nulls)
#     even though we have no real intelligence about the product —
#     downstream code can still run, just with weaker signal.
#     """

#     return {
#         "product_type": "Unknown",
#         "category": "Unknown",
#         "industry": "Unknown",
#         "technology": [],
#         "manufacturer": "Unknown",
#         "competitor_brands": [],
#         "keywords": [product] if product else [],
#     }


# def analyze_product(product):
#     """
#     Returns a full structured analysis of a product/technology/
#     service name:

#         {
#             "product": "...",
#             "product_type": "...",
#             "category": "...",
#             "industry": "...",
#             "technology": [...],
#             "manufacturer": "...",
#             "competitor_brands": [...],
#             "keywords": [...]
#         }

#     Falls back silently (never raises) to FALLBACK_ANALYSIS or a
#     generic empty-but-valid shape if OpenAI is unavailable,
#     misconfigured, rate-limited, or returns something unusable —
#     matching the resilience pattern used elsewhere in the codebase
#     (openai_service.py).
#     """

#     global _cooldown_until

#     if not product:
#         result = _generic_fallback(product)
#         result["product"] = product
#         return result

#     key = product.lower().strip()

#     # ---- Cache hit ----
#     if key in _cache:
#         return _cache[key]

#     def _finalize(analysis_dict):
#         result = dict(analysis_dict)
#         result["product"] = product
#         _cache[key] = result
#         return result

#     # ---- No API key configured: skip straight to fallback ----
#     if not OPENAI_API_KEY:
#         base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
#         return _finalize(base)

#     # ---- Cooldown active from a recent 429 ----
#     if time.time() < _cooldown_until:
#         base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
#         return _finalize(base)

#     try:
#         analysis = _call_openai(product)

#         if not analysis:
#             # Malformed/unusable response — fall back rather
#             # than returning nulls.
#             base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
#             return _finalize(base)

#         return _finalize(analysis)

#     except Exception as e:

#         # Handle rate limits with a cooldown so we don't
#         # hammer OpenAI on every subsequent request.
#         if "429" in str(e) or "rate limit" in str(e).lower():
#             _cooldown_until = time.time() + COOLDOWN_SECONDS

#         # Any failure (timeout, bad JSON, network, auth) —
#         # degrade silently to fallback data.
#         base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
#         return _finalize(base)


# def find_similar_brands_llm(product):
#     """
#     Backward-compatible wrapper: returns just the competitor
#     brand names, for callers that only need the brand list
#     (e.g. the existing CRM brand-matching step in icp_service.py).
#     """

#     return analyze_product(product).get("competitor_brands", [])

##-----------------------------------------------------------

import json
import time

from openai import OpenAI

try:
    from config import OPENAI_API_KEY
except ImportError:
    from ..config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)


# ----------------------------------------------------------
# In-memory cache: product string -> full analysis dict
# (avoids repeat OpenAI calls for the same product within
# a running server process)
# ----------------------------------------------------------
_cache = {}

# ----------------------------------------------------------
# Cooldown state for 429 handling, mirroring the pattern
# already used in openai_service.py
# ----------------------------------------------------------
_cooldown_until = 0
COOLDOWN_SECONDS = 60

# Hard cap on response size — the schema is small and bounded,
# so this is a safety net against a runaway/misbehaving response,
# not a normal operating limit.
MAX_OUTPUT_TOKENS = 400

# Fallback data used if OpenAI is unavailable, misconfigured,
# rate-limited, or returns something unusable. Kept intentionally
# small — only for the products we already knew about before the
# LLM existed. Anything not in here falls back to a generic
# "unknown product" shape rather than returning nulls.
FALLBACK_ANALYSIS = {
    "macbook": {
        "product_type": "Laptop",
        "category": "Computers",
        "industry": "Consumer Electronics",
        "technology": ["Personal Computing"],
        "manufacturer": "Apple",
        "competitor_brands": ["Dell", "HP", "Lenovo"],
        "keywords": ["Laptop", "Notebook", "Portable Computer"],
    },
    "iphone": {
        "product_type": "Smartphone",
        "category": "Mobile Devices",
        "industry": "Consumer Electronics",
        "technology": ["Mobile Computing"],
        "manufacturer": "Apple",
        "competitor_brands": ["Samsung", "Google Pixel"],
        "keywords": ["Smartphone", "Mobile Phone"],
    },
    "windows": {
        "product_type": "Operating System",
        "category": "Software",
        "industry": "Enterprise Software",
        "technology": ["Operating Systems"],
        "manufacturer": "Microsoft",
        "competitor_brands": ["Dell", "HP"],
        "keywords": ["Operating System", "OS"],
    },
}

REQUIRED_KEYS = [
    "product_type",
    "category",
    "industry",
    "technology",
    "manufacturer",
    "competitor_brands",
    "keywords",
]


SYSTEM_PROMPT = """You are a B2B market analyst.
Given a product, technology, or service name, analyze it
completely so it can be matched against a CRM of companies
and their brands.

Even if the input is vague, unusual, or not a well-known
product, make your best reasonable inference — never return
empty or null fields. Use general category knowledge if you
don't recognize the specific name.

Respond ONLY with a JSON object in exactly this shape,
nothing else, no explanations:

{
    "product_type": "short type label, e.g. Laptop",
    "category": "broader category, e.g. Computers",
    "industry": "industry this belongs to, e.g. Consumer Electronics",
    "technology": ["relevant technology areas"],
    "manufacturer": "known manufacturer, or best guess, or 'Unknown'",
    "competitor_brands": ["3 to 8 real, well-known competing brand names, most relevant first"],
    "keywords": ["3 to 6 related search keywords"]
}
"""


def _validate_and_clean(parsed):

    if not isinstance(parsed, dict):
        return None

    for key in REQUIRED_KEYS:
        if key not in parsed:
            return None

    def _clean_list(value):
        if not isinstance(value, list):
            return []
        return [
            v.strip()
            for v in value
            if isinstance(v, str) and v.strip()
        ]

    cleaned = {
        "product_type": str(parsed.get("product_type") or "Unknown").strip(),
        "category": str(parsed.get("category") or "Unknown").strip(),
        "industry": str(parsed.get("industry") or "Unknown").strip(),
        "technology": _clean_list(parsed.get("technology")),
        "manufacturer": str(parsed.get("manufacturer") or "Unknown").strip(),
        "competitor_brands": _clean_list(parsed.get("competitor_brands")),
        "keywords": _clean_list(parsed.get("keywords")),
    }

    return cleaned


def _call_openai(product):

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Product: {product}"}
        ],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=MAX_OUTPUT_TOKENS,
        timeout=10
    )

    raw = response.choices[0].message.content

    parsed = json.loads(raw)

    return _validate_and_clean(parsed)


def _generic_fallback(product):
    """
    Used when the product isn't in FALLBACK_ANALYSIS and OpenAI
    is unavailable. Keeps the schema fully populated (no nulls)
    even though we have no real intelligence about the product —
    downstream code can still run, just with weaker signal.
    """

    return {
        "product_type": "Unknown",
        "category": "Unknown",
        "industry": "Unknown",
        "technology": [],
        "manufacturer": "Unknown",
        "competitor_brands": [],
        "keywords": [product] if product else [],
    }


def analyze_product(product):
    """
    Returns a full structured analysis of a product/technology/
    service name:

        {
            "product": "...",
            "product_type": "...",
            "category": "...",
            "industry": "...",
            "technology": [...],
            "manufacturer": "...",
            "competitor_brands": [...],
            "keywords": [...]
        }

    Falls back silently (never raises) to FALLBACK_ANALYSIS or a
    generic empty-but-valid shape if OpenAI is unavailable,
    misconfigured, rate-limited, or returns something unusable —
    matching the resilience pattern used elsewhere in the codebase
    (openai_service.py).
    """

    global _cooldown_until

    if not product:
        result = _generic_fallback(product)
        result["product"] = product
        return result

    key = product.lower().strip()

    # ---- Cache hit ----
    if key in _cache:
        return _cache[key]

    def _finalize(analysis_dict):
        result = dict(analysis_dict)
        result["product"] = product
        _cache[key] = result
        return result

    # ---- No API key configured: skip straight to fallback ----
    if not OPENAI_API_KEY:
        base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
        return _finalize(base)

    # ---- Cooldown active from a recent 429 ----
    if time.time() < _cooldown_until:
        base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
        return _finalize(base)

    try:
        analysis = _call_openai(product)

        if not analysis:
            # Malformed/unusable response — fall back rather
            # than returning nulls.
            base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
            return _finalize(base)

        return _finalize(analysis)

    except Exception as e:

        # Handle rate limits with a cooldown so we don't
        # hammer OpenAI on every subsequent request.
        if "429" in str(e) or "rate limit" in str(e).lower():
            _cooldown_until = time.time() + COOLDOWN_SECONDS

        # Any failure (timeout, bad JSON, network, auth) —
        # degrade silently to fallback data.
        base = FALLBACK_ANALYSIS.get(key) or _generic_fallback(product)
        return _finalize(base)


def find_similar_brands_llm(product):
    """
    Backward-compatible wrapper: returns just the competitor
    brand names, for callers that only need the brand list
    (e.g. the existing CRM brand-matching step in icp_service.py).
    """

    return analyze_product(product).get("competitor_brands", [])