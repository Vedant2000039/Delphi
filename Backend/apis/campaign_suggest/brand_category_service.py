# brand_category_service.py
# ─────────────────────────────────────────────────────────────
# Categorizes brand names into a fixed B2B taxonomy so campaigns
# for "similar" brands (e.g. Apple <-> Dell, both "Computers &
# Hardware") can be matched even though the raw data only has
# brand names, not product categories.
#
# Flow per brand:
#   1. Check mst_tblbrand_category cache (MySQL)
#   2. GPT-only categorization using world knowledge of the brand
#   3. If "Uncategorized" -> GPT guesses the brand's official domain,
#      scrape that domain's homepage (reuses enrichment.py scraping),
#      and re-categorize using the scraped page text as context
#   4. Cache the result (including "Uncategorized" for manual review)
# ─────────────────────────────────────────────────────────────

from __future__ import annotations
import json
import os

import snowflake.connector
from apis.p3_campaign.openai_service import ask_gpt
from apis.Onboarding.enrichment import (
    fetch_html_batch,
    playwright_fetch_batch,
    is_meaningful_html,
)
from bs4 import BeautifulSoup


def _get_sf_conn():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


BRAND_CATEGORIES = [
    "Computers & Hardware",
    "Software & SaaS",
    "Cloud & Cybersecurity",
    "Telecommunications",
    "Consulting & Professional Services",
    "Financial Services & Insurance",
    "Logistics & Supply Chain",
    "Manufacturing & Industrial",
    "Healthcare & Pharma",
    "Retail & Consumer Goods",
    "Media, Entertainment & Advertising",
    "Education & Training",
    "Legal Services",
    "Real Estate & Construction",
    "Other",
]

UNCATEGORIZED = "Uncategorized"


# ══════════════════════════════════════════════════════════════
# CACHE (MST_TBLBRAND_CATEGORY in Snowflake)
# ══════════════════════════════════════════════════════════════

def get_cached_category(brand_id: int) -> dict | None:
    conn = _get_sf_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT BRAND_ID, CATEGORY, SOURCE FROM MST_TBLBRAND_CATEGORY "
            "WHERE BRAND_ID = %s",
            (brand_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {"brand_id": row[0], "category": row[1], "source": row[2]}
    finally:
        cursor.close()
        conn.close()


def save_brand_category(brand_id: int, category: str, source: str) -> None:
    conn = _get_sf_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "MERGE INTO MST_TBLBRAND_CATEGORY t USING (SELECT %s AS BRAND_ID) s "
            "ON t.BRAND_ID = s.BRAND_ID "
            "WHEN MATCHED THEN UPDATE SET CATEGORY = %s, SOURCE = %s "
            "WHEN NOT MATCHED THEN INSERT (BRAND_ID, CATEGORY, SOURCE) "
            "VALUES (%s, %s, %s)",
            (brand_id, category, source, brand_id, category, source)
        )
    finally:
        cursor.close()
        conn.close()


# ══════════════════════════════════════════════════════════════
# STEP 1 — GPT-only categorization (world knowledge)
# ══════════════════════════════════════════════════════════════

def _categorize_from_text(brand_name: str, context_text: str | None = None) -> str:
    categories_list = "\n".join(f"- {c}" for c in BRAND_CATEGORIES)

    if context_text:
        prompt = f"""Brand/Company name: "{brand_name}"

Here is text from their official website homepage:
\"\"\"
{context_text}
\"\"\"

Categories:
{categories_list}

Based on the brand name and website content, return ONLY valid JSON:
{{"category": "<one category from the list above, exactly as written>"}}

If nothing clearly indicates a category, return {{"category": "{UNCATEGORIZED}"}}
No explanation, no markdown."""
    else:
        prompt = f"""Brand/Company name: "{brand_name}"

Categories:
{categories_list}

Based on your knowledge of this brand, return ONLY valid JSON:
{{"category": "<one category from the list above, exactly as written>"}}

If you don't recognize this brand or are unsure what it sells, return:
{{"category": "{UNCATEGORIZED}"}}
No explanation, no markdown."""

    response = ask_gpt(prompt, temperature=0.0, max_tokens=60)
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean.strip())
        category = data.get("category", UNCATEGORIZED)
        return category if category in BRAND_CATEGORIES else UNCATEGORIZED
    except Exception as e:
        print(f"[BrandCategory] Failed to parse GPT response for '{brand_name}': {e}")
        return UNCATEGORIZED


def categorize_brand(brand_name: str) -> str:
    """GPT-only categorization using the brand's name."""
    return _categorize_from_text(brand_name)


# ══════════════════════════════════════════════════════════════
# STEP 2 — Domain guess + homepage scrape (fallback for unknowns)
# ══════════════════════════════════════════════════════════════

def guess_domain(brand_name: str) -> str:
    prompt = f"""What is the most likely official website domain for the company/brand "{brand_name}"?

Return ONLY valid JSON: {{"domain": "example.com"}}
If you don't know, return {{"domain": ""}}
No explanation, no markdown."""

    response = ask_gpt(prompt, temperature=0.0, max_tokens=40)
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean.strip())
        return (data.get("domain") or "").strip()
    except Exception as e:
        print(f"[BrandCategory] Failed to parse domain guess for '{brand_name}': {e}")
        return ""


async def fetch_homepage_text(domain: str) -> str:
    if not domain:
        return ""

    url = domain if domain.startswith("http") else f"https://{domain}"

    html_map = await fetch_html_batch([url])
    html = html_map.get(url, "")

    if not is_meaningful_html(html):
        pw_map = await playwright_fetch_batch([url])
        html = pw_map.get(url, "") or html

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    return text[:1500]


# ══════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════

async def categorize_brand_with_fallback(brand_id: int, brand_name: str) -> dict:
    """
    Returns {"brand_id": ..., "brand_name": ..., "category": ..., "source": "cache" | "gpt" | "gpt+scrape"}.
    Caches every result (including Uncategorized) in MST_TBLBRAND_CATEGORY.
    """
    cached = get_cached_category(brand_id)
    if cached:
        cached["brand_name"] = brand_name
        cached["source"] = "cache"
        return cached

    category = categorize_brand(brand_name)
    source = "gpt"

    if category == UNCATEGORIZED:
        domain = guess_domain(brand_name)
        if domain:
            page_text = await fetch_homepage_text(domain)
            if page_text:
                category = _categorize_from_text(brand_name, page_text)
                source = "gpt+scrape"

    save_brand_category(brand_id, category, source)
    return {"brand_id": brand_id, "brand_name": brand_name, "category": category, "source": source}
