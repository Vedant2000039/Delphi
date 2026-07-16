# intent_engine/trend_analyzer.py

from __future__ import annotations
import json
import time
import logging
import os
import sys
from dataclasses import dataclass

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# B2B Market Allowlist
# Instead of a blocklist (impossible to maintain), only keep
# countries that are real B2B markets with enterprise buyers.
# Population threshold: >5M people AND meaningful B2B economy.
# ─────────────────────────────────────────────────────────────
B2B_ALLOWLIST = {
    # Americas
    "united states", "canada", "brazil", "mexico", "argentina",
    "colombia", "chile", "peru",
    # Europe
    "united kingdom", "germany", "france", "netherlands", "spain",
    "italy", "sweden", "switzerland", "poland", "belgium",
    "portugal", "denmark", "norway", "finland", "austria",
    "czech republic", "romania", "hungary", "ukraine", "greece",
    "turkey",
    # Middle East & Africa
    "uae", "united arab emirates", "saudi arabia", "israel",
    "south africa", "egypt", "nigeria", "kenya", "ghana",
    "qatar", "kuwait", "bahrain",
    # Asia Pacific
    "india", "china", "japan", "south korea", "australia",
    "singapore", "indonesia", "malaysia", "thailand", "vietnam",
    "philippines", "new zealand", "pakistan", "bangladesh",
    "hong kong", "taiwan",
}


@dataclass
class TrendResult:
    product: str
    top_regions: list[dict]       # [{region, score, flag}]  — noise-filtered
    rising_regions: list[dict]    # [{query, value}]
    time_trend: list[dict]        # [{date, value}]
    summary: str                  # AI narrative (1 paragraph)
    recommendation: str           # Actionable campaign recommendation
    raw_available: bool = True    # False when pytrends is rate-limited


FLAG_MAP = {
    "United States": "🇺🇸", "India": "🇮🇳", "United Kingdom": "🇬🇧",
    "Germany": "🇩🇪", "Canada": "🇨🇦", "Australia": "🇦🇺",
    "France": "🇫🇷", "Brazil": "🇧🇷", "Japan": "🇯🇵", "China": "🇨🇳",
    "Singapore": "🇸🇬", "Netherlands": "🇳🇱", "Sweden": "🇸🇪",
    "Israel": "🇮🇱", "UAE": "🇦🇪", "South Korea": "🇰🇷",
    "Mexico": "🇲🇽", "Italy": "🇮🇹", "Spain": "🇪🇸", "Indonesia": "🇮🇩",
    "Philippines": "🇵🇭", "Nigeria": "🇳🇬", "South Africa": "🇿🇦",
    "Pakistan": "🇵🇰", "Bangladesh": "🇧🇩", "Malaysia": "🇲🇾",
    "Thailand": "🇹🇭", "Vietnam": "🇻🇳", "Poland": "🇵🇱",
    "Turkey": "🇹🇷", "Argentina": "🇦🇷", "Colombia": "🇨🇴",
    "Egypt": "🇪🇬", "Kenya": "🇰🇪", "Saudi Arabia": "🇸🇦",
}


def _get_flag(region: str) -> str:
    for name, flag in FLAG_MAP.items():
        if name.lower() in region.lower() or region.lower() in name.lower():
            return flag
    return "🌍"


def _filter_noise(regions: list[dict]) -> list[dict]:
    """
    Keep only real B2B markets from the allowlist.
    Falls back to top-8 by score if allowlist yields < 3 results.
    """
    filtered = [r for r in regions if r["region"].lower() in B2B_ALLOWLIST]
    if len(filtered) >= 3:
        return filtered
    # Fallback: score-sort and return top 8 (better than nothing)
    log.warning("[TrendFilter] Allowlist too restrictive — returning top 8 by score")
    return sorted(regions, key=lambda x: x["score"], reverse=True)[:8]


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
        pass
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        def ask_gpt(prompt, temperature=0.7, max_tokens=500):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        return ask_gpt
    except Exception as e:
        log.error(f"[TrendAnalyzer] Cannot load ask_gpt: {e}")
        return None


def _fetch_google_trends(keyword: str, timeframe: str = "today 12-m") -> dict:
    from pytrends.request import TrendReq
    pytrends = TrendReq(hl="en-US", tz=330, timeout=(10, 25), retries=1, backoff_factor=1.0)
    pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo="", gprop="")
    result = {"by_region": [], "over_time": [], "rising": []}

    # Step 1: Interest by region (most important — never skip)
    try:
        df = pytrends.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=False)
        df = df.sort_values(keyword, ascending=False)
        raw = [
            {"region": str(idx), "score": int(row[keyword]), "flag": _get_flag(str(idx))}
            for idx, row in df.iterrows()
            if int(row[keyword]) > 0
        ]
        result["by_region"] = _filter_noise(raw)[:12]
    except Exception as e:
        log.warning(f"[Trends] by_region failed: {e}")
        raise  # propagate so caller uses fallback

    time.sleep(2)  # be polite between requests

    # Step 2: Interest over time (optional — skip gracefully on 429)
    try:
        df_time = pytrends.interest_over_time()
        if not df_time.empty and keyword in df_time.columns:
            result["over_time"] = [
                {"date": str(ts.date()), "value": int(val)}
                for ts, val in zip(df_time.index, df_time[keyword])
            ][-24:]
    except Exception as e:
        # 429 rate limit — over_time is optional, just skip it
        log.info(f"[Trends] over_time skipped (rate limit or error): {type(e).__name__}")
        result["over_time"] = []

    time.sleep(2)

    # Step 3: Rising queries (optional — skip gracefully on 429)
    try:
        related = pytrends.related_queries()
        rising_df = related.get(keyword, {}).get("rising")
        if rising_df is not None and not rising_df.empty:
            result["rising"] = [
                {"query": str(row["query"]), "value": str(row["value"])}
                for _, row in rising_df.head(8).iterrows()
            ]
    except Exception as e:
        log.info(f"[Trends] rising skipped (rate limit or error): {type(e).__name__}")
        result["rising"] = []

    return result


FALLBACK_DATA = [
    {"region": "United States",  "score": 100, "flag": "🇺🇸"},
    {"region": "India",          "score": 82,  "flag": "🇮🇳"},
    {"region": "United Kingdom", "score": 71,  "flag": "🇬🇧"},
    {"region": "Germany",        "score": 60,  "flag": "🇩🇪"},
    {"region": "Australia",      "score": 55,  "flag": "🇦🇺"},
    {"region": "Canada",         "score": 52,  "flag": "🇨🇦"},
    {"region": "Singapore",      "score": 45,  "flag": "🇸🇬"},
    {"region": "UAE",            "score": 40,  "flag": "🇦🇪"},
]


def _generate_narrative(product: str, regions: list[dict], rising: list[dict],
                         context: dict, ask_gpt) -> tuple[str, str]:
    """Generate SUMMARY + RECOMMENDATION using GPT."""
    region_str = ", ".join(
        f"{r['flag']} {r['region']} ({r['score']}/100)" for r in regions[:6]
    ) or "data unavailable"
    rising_str = ", ".join(r["query"] for r in rising[:5]) or "none detected"
    ctx_note = ""
    if context:
        filled = {k: v for k, v in context.items() if v}
        if filled:
            ctx_note = f"\nUser's existing campaign context: {json.dumps(filled)}"

    prompt = f"""You are a senior B2B market intelligence analyst.

Product being researched: "{product}"
Top regions (noise-filtered, B2B relevant): {region_str}
Rising related searches: {rising_str}{ctx_note}

Write exactly two labelled sections:

SUMMARY: 2-3 sentences. What does this trend data mean for someone selling {product} to businesses? Name the top 2-3 markets and why they matter (enterprise density, buyer maturity, growth rate). Be specific.

RECOMMENDATION: 2 sentences. Which 2-3 regions to prioritise and why. Be direct and actionable.

Return ONLY these two lines, no other text:
SUMMARY: <text>
RECOMMENDATION: <text>"""

    try:
        raw = ask_gpt(prompt, temperature=0.4, max_tokens=250)
        summary = recommendation = ""
        for line in raw.strip().split("\n"):
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("RECOMMENDATION:"):
                recommendation = line.replace("RECOMMENDATION:", "").strip()
        if not summary:
            summary = raw[:200].strip()
        if not recommendation:
            recommendation = f"Prioritise {regions[0]['region']} and {regions[1]['region']} — they show the highest B2B intent for {product}." if len(regions) >= 2 else ""
        return summary, recommendation
    except Exception as e:
        log.warning(f"[TrendNarrative] GPT failed: {e}")
        top = regions[0]["region"] if regions else "the US"
        return (
            f"Search interest for {product} is strongest in {top}.",
            f"Focus your campaign on {region_str}."
        )


def analyze_trends(product: str, context: dict | None = None,
                   timeframe: str = "today 12-m") -> TrendResult:
    if context is None:
        context = {}

    ask_gpt = _get_ask_gpt()
    if ask_gpt is None:
        def ask_gpt(p, **kw): return ""

    raw_available = True
    trend_data = {"by_region": [], "over_time": [], "rising": []}

    try:
        log.info(f"[TrendAnalyzer] Fetching Google Trends for: {product!r}")
        trend_data = _fetch_google_trends(product, timeframe=timeframe)
        raw_available = True
    except Exception as e:
        log.warning(f"[TrendAnalyzer] Fetch failed ({e}) — using fallback")
        trend_data["by_region"] = FALLBACK_DATA
        raw_available = False

    if not trend_data["by_region"]:
        trend_data["by_region"] = FALLBACK_DATA
        raw_available = False

    # Always filter noise before narrative generation
    clean_regions = _filter_noise(trend_data["by_region"])[:10]

    summary, recommendation = _generate_narrative(
        product, clean_regions, trend_data.get("rising", []), context, ask_gpt
    )

    return TrendResult(
        product        = product,
        top_regions    = clean_regions,
        rising_regions = trend_data.get("rising", []),
        time_trend     = trend_data.get("over_time", []),
        summary        = summary,
        recommendation = recommendation,
        raw_available  = raw_available,
    )