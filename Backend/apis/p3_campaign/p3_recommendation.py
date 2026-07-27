# apis/p3_campaign/p3_recommendation.py

from __future__ import annotations

import json

from apis.context_engine.openai_service import ask_gpt


# ------------------------------------------------------------------
# Convert raw campaign records into a UI-friendly format
# ------------------------------------------------------------------
def _build_display_campaigns(matched_campaigns: list[dict]) -> list[dict]:
    """
    Extracts only the targeting fields required for displaying
    campaign recommendations to the user.
    """

    # Helper to retrieve values regardless of key casing
    def _get(row, *keys):
        for key in keys:
            value = row.get(key) or row.get(key.upper()) or row.get(key.lower())
            if value:
                return str(value).strip()
        return "Not specified"

    display = []

    # Build display model for the first five campaigns
    for index, campaign in enumerate(matched_campaigns[:5]):
        display.append({
            "index": index + 1,
            "job_level": _get(campaign, "target_job_level"),
            "job_function": _get(campaign, "target_job_function"),
            "employee_size": _get(campaign, "target_employee_size"),
            "revenue_range": _get(campaign, "target_revenue_size"),
            "geography": _get(campaign, "target_geography"),
            "quantity": _get(campaign, "effective_total_quantity"),
        })

    return display


# ------------------------------------------------------------------
# Generate campaign recommendation using GPT
# ------------------------------------------------------------------
def _generate_recommendation_text(
    geography: str,
    industry: str,
    selected_product: str,
    display_campaigns: list[dict],
    company_profile: dict | None,
) -> str:
    """
    Generates a short targeting recommendation based on
    historical campaign profiles or general B2B best practices.
    """

    # Build prompt when historical campaigns are available
    if display_campaigns:
        prompt = f"""You are a senior B2B campaign strategist at Delphi AI.

A user wants to run a campaign for their product: "{selected_product}"
Target geography: {geography}
Target industry: {industry}

Based on the following similar past campaign targeting profiles
(de-identified), write a short targeting recommendation:

{json.dumps(display_campaigns, indent=2)}

Rules:
- Write 2–3 sentences maximum.
- Sound like a sharp consultant giving a specific recommendation.
- Do NOT mention campaign names, codes, client names, or numbers of campaigns.
- Do NOT say "based on X campaigns" or "based on past data".
- Do NOT use filler phrases like "Great!" or "Certainly!".
- Mention specific job levels, functions, company sizes, or revenue
  ranges that appear consistently across the profiles.
"""

    # Build prompt when no campaign history is available
    else:
        prompt = f"""You are a senior B2B campaign strategist at Delphi AI.

A user wants to run a campaign for their product: "{selected_product}"
Target geography: {geography}
Target industry: {industry}

No direct historical campaign data is available for this combination.

Write a short, confident targeting recommendation based on general
B2B best practices for this industry and geography.

Rules:
- Write 2–3 sentences maximum.
- Do NOT say "I don't have data" or "no campaigns found".
- Do NOT use filler phrases.
- Be specific about job levels, functions, or company sizes typical for this industry.
"""

    try:
        return ask_gpt(
            prompt,
            temperature=0.6,
            max_tokens=180,
        )

    except Exception as e:
        print(f"[P3Recommendation] GPT error: {e}")

        return (
            f"For {industry} in {geography}, I recommend targeting "
            f"mid-to-senior decision makers at relevant companies. "
            f"Here are some targeting profiles that match your criteria."
        )


# ------------------------------------------------------------------
# Generate recommendation and campaign display data
# ------------------------------------------------------------------
def generate_recommendation(
    geography: str,
    industry: str,
    selected_product: str,
    matched_campaigns: list[dict],
    company_profile: dict | None = None,
) -> tuple[str, list[dict]]:
    """
    Generates the recommendation text and prepares campaign
    data for display.
    """

    # Prepare campaign data for the UI
    display_campaigns = _build_display_campaigns(matched_campaigns)

    # Generate recommendation text
    recommendation_text = _generate_recommendation_text(
        geography=geography,
        industry=industry,
        selected_product=selected_product,
        display_campaigns=display_campaigns,
        company_profile=company_profile,
    )

    return recommendation_text, display_campaigns