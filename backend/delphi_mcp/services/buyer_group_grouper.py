"""
buyer_group_grouper.py

Takes the aggregated candidate rows from buyer_group_service and asks
GPT-4.1 to perform semantic grouping: combine job_level + job_function
(+ employee/revenue context) into named Buyer Groups with roles,
seniority, primary function, decision influence, and a one-line "why
this group" rationale — matching the UI in the Discover Buyer Groups
screen.

SQL = evidence. LLM = interpretation. This file is only interpretation:
it never sees individual leads, only the aggregated candidate rows.
"""

import json
import logging

try:
    from openai_service import ask_gpt
except ImportError:
    from ..openai_service import ask_gpt

logger = logging.getLogger("buyer_group_grouper")

SYSTEM_PROMPT = """You are a B2B go-to-market analyst inside Delphi, a \
buyer-intelligence platform. You will be given aggregated statistics \
about job levels and job functions found within a company's ICP-qualified \
lead population, along with the employee-size and revenue-size bands those \
leads fall into. You never see individual people.

Your job is to cluster these statistical rows into 2-4 named Buyer Groups \
that a sales/marketing team would recognize (e.g. "IT & Infrastructure", \
"Finance & Procurement", "Business Leadership"). Merge related job_level + \
job_function combinations into the same group where they represent the \
same real-world buying role, even if the raw rows are split across levels \
(e.g. IT Director and IT Manager both belong in an IT group).

For each group return:
- group_name: short, human-readable (2-4 words)
- roles: 3-5 representative job titles a person in this group would hold \
(infer plausible titles from job_function + job_level, do not invent \
unrelated titles)
- goals: 2-3 short phrases describing what this group cares about when \
evaluating a purchase
- decision_influence: one of "HIGH", "MEDIUM", "LOW"
- decision_role: one of "Budget Approver", "Evaluator", "Sponsor / Champion", \
"End User", "Gatekeeper"
- why_this_group: one sentence explaining why this cluster matters for \
this ICP

Also return an "insight" field: one sentence of aggregate analysis across \
all groups (e.g. how often two groups co-occur, how influence correlates \
with deal outcomes) — ONLY if the data supports it; otherwise use a \
neutral summary sentence about the population size and dominant group.

Respond with ONLY valid JSON, no markdown fences, no preamble, in exactly \
this shape:

{
  "buyer_groups": [
    {
      "group_name": "string",
      "roles": ["string", "..."],
      "goals": ["string", "..."],
      "decision_influence": "HIGH|MEDIUM|LOW",
      "decision_role": "string",
      "why_this_group": "string"
    }
  ],
  "insight": "string"
}
"""


def build_user_prompt(candidates: list[dict], brand_name: str, product_name: str) -> str:
    payload = {
        "brand": brand_name,
        "product": product_name,
        "job_patterns": candidates,
    }
    return (
        "Here are the aggregated buyer-group candidate rows for this "
        "ICP-qualified population:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Cluster these into named Buyer Groups per the instructions."
    )


def generate_buyer_groups(
    candidates: list[dict], brand_name: str = "", product_name: str = ""
) -> dict:
    """
    Returns:
        {
            "buyer_groups": [...],
            "insight": "..."
        }
    or a safe fallback dict if the LLM call fails / returns malformed JSON.
    Never raises.
    """
    if not candidates:
        return {
            "buyer_groups": [],
            "insight": "Not enough qualified leads were found to identify distinct buyer groups yet.",
        }

    user_prompt = build_user_prompt(candidates, brand_name, product_name)

    try:
        raw_response = ask_gpt(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model="gpt-4.1",
            response_format="json",
        )
    except Exception as exc:
        logger.error("GPT-4.1 buyer-group call failed: %s", exc)
        return _fallback_from_candidates(candidates)

    # Empty-response guard — ask_gpt() can silently return "" on failure.
    if not raw_response or not raw_response.strip():
        logger.warning("ask_gpt returned empty response for buyer-group grouping.")
        return _fallback_from_candidates(candidates)

    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse buyer-group LLM JSON: %s | raw=%s", exc, raw_response[:500])
        return _fallback_from_candidates(candidates)

    if "buyer_groups" not in parsed or not isinstance(parsed["buyer_groups"], list):
        logger.error("Buyer-group LLM response missing expected shape: %s", parsed)
        return _fallback_from_candidates(candidates)

    return parsed


def _fallback_from_candidates(candidates: list[dict]) -> dict:
    """
    Degrades gracefully: if the LLM is unavailable, group raw candidates
    by job_function only (no semantic merging) so the frontend still gets
    something usable instead of an empty screen.
    """
    grouped: dict[str, list[dict]] = {}
    for row in candidates:
        fn = row.get("job_function", "Other")
        grouped.setdefault(fn, []).append(row)

    buyer_groups = []
    for fn, rows in grouped.items():
        levels = sorted({r.get("job_level", "") for r in rows if r.get("job_level")})
        buyer_groups.append(
            {
                "group_name": fn,
                "roles": levels[:5] or [fn],
                "goals": [],
                "decision_influence": "MEDIUM",
                "decision_role": "Evaluator",
                "why_this_group": f"Represents the {fn} function within your ICP-qualified population.",
            }
        )

    return {
        "buyer_groups": buyer_groups,
        "insight": "Groups shown are based on raw job-function aggregation; AI-generated grouping was unavailable.",
    }