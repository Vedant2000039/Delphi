# ai_validator.py
# ─────────────────────────────────────────────────────────────
# OpenAI validation + narrative generation layer.
# Takes the scored lead list and produces:
#   • a validation flag per lead (any anomalies?)
#   • a plain-English insight summary for the full result set
#   • a per-lead "why this lead" blurb
# ─────────────────────────────────────────────────────────────

from __future__ import annotations
import json
import logging
from .openai_service import ask_gpt

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# PER-LEAD "WHY THIS LEAD" BLURB
# ══════════════════════════════════════════════════════════════

def generate_lead_blurb(lead: dict) -> str:
    """
    Generate a 1-2 sentence natural-language explanation of why
    this lead ranks highly, based on their scoring profile.
    """
    prompt = f"""You are a senior B2B sales strategist.

Write a 1-2 sentence insight explaining why this lead is a strong match,
based on their scoring data. Be specific. Sound like a consultant, not a chatbot.
Do NOT start with "This lead" — vary the opening.

Lead data:
- Name: {lead.get('name', 'Unknown')}
- Title: {lead.get('job_title', '')} ({lead.get('job_level', '')})
- Company: {lead.get('company', '')}
- Industry: {lead.get('industry', '')}
- Country: {lead.get('country', '')}
- Propensity Score: {lead.get('propensity_score', 0)}/100
- ICP Score: {lead.get('icp_score', 0)}/100
- Persona: {lead.get('persona', '')} ({lead.get('persona_tier', '')})
- Priority: {lead.get('priority', '')}
- Recommended Action: {lead.get('recommended_action', '')}"""

    try:
        return ask_gpt(prompt, temperature=0.6, max_tokens=120)
    except Exception as e:
        log.warning(f"Blurb generation failed for lead {lead.get('lead_id')}: {e}")
        return ""


# ══════════════════════════════════════════════════════════════
# RESULT-SET SUMMARY
# ══════════════════════════════════════════════════════════════

def generate_results_summary(
    context: dict,
    leads: list[dict]
) -> str:
    """
    Produce a concise executive summary of the full result set.
    """
    if not leads:
        return "No high-scoring leads were found matching your criteria. Consider broadening the filters."

    top3 = leads[:3]
    avg_combined = round(sum(l["combined_score"] for l in leads) / len(leads), 1)
    priority_dist = {}
    for l in leads:
        p = l.get("priority", "Unknown")
        priority_dist[p] = priority_dist.get(p, 0) + 1

    prompt = f"""You are a B2B intelligence analyst presenting lead results to a sales team.

Targeting context:
{json.dumps(context, indent=2)}

Results summary:
- Total leads found: {len(leads)}
- Average combined score: {avg_combined}/100
- Priority distribution: {json.dumps(priority_dist)}
- Top 3 leads: {json.dumps([
    {{'name': l['name'], 'company': l['company'], 'title': l['job_title'],
     'score': l['combined_score'], 'priority': l['priority']}}
    for l in top3
], indent=2)}

Write a SHORT executive summary (3-4 sentences) that:
1. Describes the quality of this lead set
2. Highlights the most promising segment or pattern
3. Gives one clear next-step recommendation for the sales team

Be direct and analytical. No marketing fluff."""

    try:
        return ask_gpt(prompt, temperature=0.5, max_tokens=200)
    except Exception as e:
        log.warning(f"Summary generation failed: {e}")
        return f"Found {len(leads)} high-quality leads matching your targeting criteria."


# ══════════════════════════════════════════════════════════════
# ANOMALY / VALIDATION CHECK
# ══════════════════════════════════════════════════════════════

def validate_lead_set(leads: list[dict]) -> dict:
    """
    Run a quick GPT validation pass over the lead set.
    Returns a dict with 'valid' bool and 'notes' string.
    Catches issues like: all leads suppressed, zero ICP score,
    impossible score combinations, etc.
    """
    if not leads:
        return {"valid": False, "notes": "No leads returned from the scoring engine."}

    issues = []

    suppressed_count = sum(1 for l in leads if l.get("suppressed"))
    if suppressed_count == len(leads):
        issues.append("All returned leads are suppressed.")

    zero_icp = sum(1 for l in leads if l.get("icp_score", 0) == 0)
    if zero_icp > len(leads) * 0.7:
        issues.append(f"{zero_icp} of {len(leads)} leads have zero ICP score — ICP model may not have data.")

    zero_propensity = sum(1 for l in leads if l.get("propensity_score", 0) == 0)
    if zero_propensity > len(leads) * 0.7:
        issues.append(f"{zero_propensity} leads have zero propensity score — propensity model may lack engagement data.")

    if not issues:
        return {"valid": True, "notes": ""}

    prompt = f"""You are a data quality analyst reviewing B2B lead scoring results.

Issues detected:
{chr(10).join(f'- {i}' for i in issues)}

Write ONE short sentence (max 20 words) warning the user about this data quality issue."""

    try:
        note = ask_gpt(prompt, temperature=0.3, max_tokens=60)
        return {"valid": False, "notes": note}
    except:
        return {"valid": False, "notes": "; ".join(issues)}


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def validate_and_enrich(
    context: dict,
    leads: list[dict]
) -> dict:
    """
    Full AI validation + enrichment pass over the scored lead list.
    Adds 'insight' blurb to each lead, generates a summary, validates quality.

    Returns:
        {
            "summary": str,
            "validation": { "valid": bool, "notes": str },
            "leads": [...enriched lead dicts...]
        }
    """
    validation = validate_lead_set(leads)
    summary    = generate_results_summary(context, leads)

    # Add per-lead blurb (only for top 5 to save tokens)
    enriched = []
    for i, lead in enumerate(leads):
        if i < 5:
            lead["insight"] = generate_lead_blurb(lead)
        else:
            lead["insight"] = ""
        enriched.append(lead)

    return {
        "summary":    summary,
        "validation": validation,
        "leads":      enriched,
    }