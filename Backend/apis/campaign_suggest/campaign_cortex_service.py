# ==============================================================================
# File: campaign_cortex_service.py
#
# Description:
# This module interacts with Snowflake Cortex Analyst to retrieve historical
# campaign information using the CAMPAIGN_DISCOVER semantic model.
#
# It provides APIs to:
#   1. Find campaigns that match a target Industry and Geography.
#   2. Optionally filter campaigns by Brand Category.
#   3. Retrieve ICP (Ideal Customer Profile) targeting details
#      for a selected campaign.
#
# Note:
# Geography and Industry values are passed exactly as received from the
# frontend. No normalization or mapping is performed because the semantic
# model stores the original database values.
#
# Example:
#     ✔ Banking
#     ✘ Finance
#
#     ✔ Afghanistan
#     ✘ AF
#
# ==============================================================================

from __future__ import annotations

# ------------------------------------------------------------------------------
# Internal Imports
# ------------------------------------------------------------------------------

from ..context_engine.cortex_service import query_cortex_analyst


# ==============================================================================
# Campaign Search
# ==============================================================================

def find_similar_campaigns(
    geography: str,
    industry: str,
    brand_category: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieves historical campaigns that match the specified
    geography and industry.

    If a brand category is provided, the search is further
    restricted to campaigns whose brands belong to the same
    business category.

    This enables discovering campaigns for similar brands even
    when the exact brand has never been used before.

    Example
    -------
    Apple
        ↓

    Category:
        Computers & Hardware

        ↓

    Similar Campaigns:
        Dell
        Lenovo
        HP
        Acer

    Parameters
    ----------
    geography : str
        Geographic location stored in the database.

    industry : str
        Industry name stored in the database.

    brand_category : str | None, optional
        Business category of the selected brand.

    limit : int, default=5
        Maximum number of campaigns to return.

    Returns
    -------
    list[dict]
        List of campaign records returned by Snowflake Cortex.
    """

    # --------------------------------------------------------------------------
    # Build Optional Brand Category Filter
    # --------------------------------------------------------------------------

    category_clause = ""

    if brand_category:
        category_clause = (
            f"and the order's brand has a category "
            f"(via MST_TBLBRAND_CATEGORY.CATEGORY) "
            f"of '{brand_category}' "
        )

    # --------------------------------------------------------------------------
    # Build Natural Language Prompt for Cortex Analyst
    # --------------------------------------------------------------------------

    prompt = (
        f"Show campaigns where engaged leads have "
        f"STANDARD_INDUSTRY_DESC = '{industry}' "
        f"and LOCATION_DESC = '{geography}' "
        f"{category_clause}. "

        f"Include "

        f"CAMPAIGN_ID, "
        f"CAMPAIGN_DESC, "
        f"INSERTION_ORDER_NUMBER, "
        f"EMPLOYEE_SIZE_DESC, "
        f"REVENUE_SIZE_DESC, "
        f"EFFECTIVE_TOTAL_QUANTITY, "
        f"BRAND_NAME, "
        f"CATEGORY. "

        f"Limit {limit}."
    )

    # --------------------------------------------------------------------------
    # Execute Cortex Query
    # --------------------------------------------------------------------------

    return query_cortex_analyst(
        prompt,
        model="campaign"
    )


# ==============================================================================
# Campaign ICP Details
# ==============================================================================

def get_campaign_icp_details(campaign_code: str) -> list[dict]:
    """
    Retrieves the ICP (Ideal Customer Profile) targeting details
    for a specific campaign.

    The returned information describes the audience that engaged
    with the selected campaign.

    Parameters
    ----------
    campaign_code : str
        Campaign ID.

    Returns
    -------
    list[dict]

        Campaign targeting details including:

        • Job Function
        • Job Level
        • Employee Size
        • Revenue Size
        • Geography
        • Number of Engaged Leads
    """

    # --------------------------------------------------------------------------
    # Build Cortex Analyst Prompt
    # --------------------------------------------------------------------------

    prompt = (
        f"For campaign with CAMPAIGN_ID = '{campaign_code}', "

        f"show the targeting details of engaged leads. "

        f"Include "

        f"JOBFUNCTION_DESC, "
        f"JOB_LEVEL_DESC, "
        f"EMPLOYEE_SIZE_DESC, "
        f"REVENUE_SIZE_DESC, "
        f"LOCATION_DESC, "

        f"and count of engaged leads."
    )

    # --------------------------------------------------------------------------
    # Execute Cortex Query
    # --------------------------------------------------------------------------

    return query_cortex_analyst(
        prompt,
        model="campaign"
    )