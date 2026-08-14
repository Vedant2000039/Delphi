# import json
# import time

# from openai import OpenAI

# from config import OPENAI_API_KEY


# client = OpenAI(api_key=OPENAI_API_KEY)

# _cooldown_until = 0
# COOLDOWN_SECONDS = 60
# MAX_OUTPUT_TOKENS = 500


# SYSTEM_PROMPT = """You are a B2B sales strategist. You are given
# aggregated statistics about historical campaign leads (never raw
# lead records — only counts and percentages) for a product a user
# is targeting. Turn this into a clear Ideal Customer Profile
# summary a salesperson can act on immediately.

# Important: the input parameters are TOP-N breakdowns, not single
# facts — e.g. Employee Size may list 2-3 ranges. Treat these as
# a distribution, not one rigid answer. Summarize them as a
# combined range or short list where natural (e.g. "500-1000
# employees" if the top values are adjacent bands, or list 2-3
# job titles for decision makers).

# Respond ONLY with a JSON object in exactly this shape, nothing
# else, no explanations outside the JSON:

# {
#     "companies": "1-2 sentence description of the ideal company profile (industry, size, revenue)",
#     "decision_makers": ["job title 1", "job title 2", "job title 3"],
#     "regions": ["region 1", "region 2"],
#     "buying_intent": "1 sentence describing what these companies are likely trying to do/buy",
#     "why": "1-2 sentence explanation grounded in the actual stats given (mention frequency/percentage patterns, not raw leads)"
# }
# """


# def _build_user_message(
#     product_analysis,
#     ideal_snapshot,
#     top_regions,
#     total_leads,
#     campaign_count,
#     client_count
# ):

#     payload = {
#         "product": product_analysis.get("product"),
#         "product_type": product_analysis.get("product_type"),
#         "category": product_analysis.get("category"),
#         "industry": product_analysis.get("industry"),
#         "competitor_brands": product_analysis.get("competitor_brands"),
#         "ideal_snapshot": ideal_snapshot,
#         "top_regions": top_regions,
#         "total_qualified_leads": total_leads,
#         "matched_campaign_count": campaign_count,
#         "matched_client_count": client_count
#     }

#     return json.dumps(payload, default=str)


# def _fallback_insight(product_analysis, ideal_snapshot, top_regions, total_leads):
#     """
#     Deterministic, non-LLM summary — used if OpenAI is
#     unavailable. Not as polished as the LLM version, but never
#     empty and never exposes raw lead data.
#     """

#     def _values_for(param_name):
#         return [
#             row.get("ideal_value")
#             for row in ideal_snapshot
#             if row.get("parameter") == param_name
#         ]

#     employee_sizes = _values_for("Employee Size")
#     revenue_sizes = _values_for("Revenue Size")
#     job_levels = _values_for("Job Level")
#     job_functions = _values_for("Job Function")

#     industry = product_analysis.get("industry", "the target")

#     companies = (
#         f"{industry} companies"
#         + (f" with {', '.join(employee_sizes)} employees" if employee_sizes else "")
#         + (f" and revenue in the {', '.join(revenue_sizes)} range" if revenue_sizes else "")
#         + "."
#     )

#     decision_makers = list(dict.fromkeys(job_levels + job_functions))[:5]

#     regions = [r.get("region") for r in top_regions] if top_regions else []

#     return {
#         "companies": companies,
#         "decision_makers": decision_makers or ["Not enough data"],
#         "regions": regions or ["Not enough data"],
#         "buying_intent": (
#             f"Organizations evaluating or modernizing solutions "
#             f"related to {product_analysis.get('category', 'this category')}."
#         ),
#         "why": (
#             f"Based on {total_leads} historically qualified leads "
#             f"across matched campaigns."
#         )
#     }


# def generate_icp_insight(
#     product_analysis,
#     ideal_snapshot,
#     top_regions,
#     total_leads,
#     campaign_count,
#     client_count
# ):
#     """
#     Produces the final human-facing ICP summary. Never receives
#     or exposes individual lead records — only aggregated stats.
#     Falls back silently to a deterministic summary if OpenAI is
#     unavailable, rate-limited, or misconfigured.
#     """

#     global _cooldown_until

#     if not OPENAI_API_KEY or time.time() < _cooldown_until:
#         return _fallback_insight(
#             product_analysis, ideal_snapshot, top_regions, total_leads
#         )

#     try:
#         user_message = _build_user_message(
#             product_analysis,
#             ideal_snapshot,
#             top_regions,
#             total_leads,
#             campaign_count,
#             client_count
#         )

#         response = client.chat.completions.create(
#             model="gpt-4.1",
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": user_message}
#             ],
#             temperature=0.2,
#             response_format={"type": "json_object"},
#             max_tokens=MAX_OUTPUT_TOKENS,
#             timeout=15
#         )

#         raw = response.choices[0].message.content
#         parsed = json.loads(raw)

#         required = ["companies", "decision_makers", "regions", "buying_intent", "why"]

#         if not all(k in parsed for k in required):
#             return _fallback_insight(
#                 product_analysis, ideal_snapshot, top_regions, total_leads
#             )

#         return parsed

#     except Exception as e:

#         if "429" in str(e) or "rate limit" in str(e).lower():
#             _cooldown_until = time.time() + COOLDOWN_SECONDS

#         return _fallback_insight(
#             product_analysis, ideal_snapshot, top_regions, total_leads
#         )

##------------------------------------------------------------------

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
aggregated statistics about historical campaign leads (never raw
lead records — only counts and percentages) for a product a user
is targeting. Turn this into a clear Ideal Customer Profile
summary a salesperson can act on immediately.

Important: the input parameters are TOP-N breakdowns, not single
facts — e.g. Employee Size may list 2-3 ranges. Treat these as
a distribution, not one rigid answer. Summarize them as a
combined range or short list where natural (e.g. "500-1000
employees" if the top values are adjacent bands, or list 2-3
job titles for decision makers).

Respond ONLY with a JSON object in exactly this shape, nothing
else, no explanations outside the JSON:

{
    "companies": "1-2 sentence description of the ideal company profile (industry, size, revenue)",
    "decision_makers": ["job title 1", "job title 2", "job title 3"],
    "regions": ["region 1", "region 2"],
    "buying_intent": "1 sentence describing what these companies are likely trying to do/buy",
    "why": "1-2 sentence explanation grounded in the actual stats given (mention frequency/percentage patterns, not raw leads)"
}
"""


def _build_user_message(
    product_analysis,
    ideal_snapshot,
    top_regions,
    total_leads,
    campaign_count,
    client_count
):

    payload = {
        "product": product_analysis.get("product"),
        "product_type": product_analysis.get("product_type"),
        "category": product_analysis.get("category"),
        "industry": product_analysis.get("industry"),
        "competitor_brands": product_analysis.get("competitor_brands"),
        "ideal_snapshot": ideal_snapshot,
        "top_regions": top_regions,
        "total_qualified_leads": total_leads,
        "matched_campaign_count": campaign_count,
        "matched_client_count": client_count
    }

    return json.dumps(payload, default=str)


def _fallback_insight(product_analysis, ideal_snapshot, top_regions, total_leads):
    """
    Deterministic, non-LLM summary — used if OpenAI is
    unavailable. Not as polished as the LLM version, but never
    empty and never exposes raw lead data.
    """

    def _values_for(param_name):
        return [
            row.get("ideal_value")
            for row in ideal_snapshot
            if row.get("parameter") == param_name
        ]

    employee_sizes = _values_for("Employee Size")
    revenue_sizes = _values_for("Revenue Size")
    job_levels = _values_for("Job Level")
    job_functions = _values_for("Job Function")

    industry = product_analysis.get("industry", "the target")

    companies = (
        f"{industry} companies"
        + (f" with {', '.join(employee_sizes)} employees" if employee_sizes else "")
        + (f" and revenue in the {', '.join(revenue_sizes)} range" if revenue_sizes else "")
        + "."
    )

    decision_makers = list(dict.fromkeys(job_levels + job_functions))[:5]

    regions = [r.get("region") for r in top_regions] if top_regions else []

    return {
        "companies": companies,
        "decision_makers": decision_makers or ["Not enough data"],
        "regions": regions or ["Not enough data"],
        "buying_intent": (
            f"Organizations evaluating or modernizing solutions "
            f"related to {product_analysis.get('category', 'this category')}."
        ),
        "why": (
            f"Based on {total_leads} historically qualified leads "
            f"across matched campaigns."
        )
    }


def generate_icp_insight(
    product_analysis,
    ideal_snapshot,
    top_regions,
    total_leads,
    campaign_count,
    client_count
):
    """
    Produces the final human-facing ICP summary. Never receives
    or exposes individual lead records — only aggregated stats.
    Falls back silently to a deterministic summary if OpenAI is
    unavailable, rate-limited, or misconfigured.
    """

    global _cooldown_until

    if not OPENAI_API_KEY or time.time() < _cooldown_until:
        return _fallback_insight(
            product_analysis, ideal_snapshot, top_regions, total_leads
        )

    try:
        user_message = _build_user_message(
            product_analysis,
            ideal_snapshot,
            top_regions,
            total_leads,
            campaign_count,
            client_count
        )

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

        required = ["companies", "decision_makers", "regions", "buying_intent", "why"]

        if not all(k in parsed for k in required):
            return _fallback_insight(
                product_analysis, ideal_snapshot, top_regions, total_leads
            )

        return parsed

    except Exception as e:

        if "429" in str(e) or "rate limit" in str(e).lower():
            _cooldown_until = time.time() + COOLDOWN_SECONDS

        return _fallback_insight(
            product_analysis, ideal_snapshot, top_regions, total_leads
        )