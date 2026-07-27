# suggestion_engine.py
from .taxonomy_service import (
    get_industries,
    get_job_functions,
    get_job_levels,
    get_employee_sizes,
    get_revenue_ranges,
    get_industry_domains,
    get_industry_domains_by_industry,
)

# Static geography suggestions (top B2B markets)
GEOGRAPHY_SUGGESTIONS = [
    "USA", "United Kingdom", "India", "Germany", "Australia",
    "Canada", "Singapore", "UAE", "France", "Netherlands"
]


def get_suggestions(context: dict, next_field: str) -> dict:
    """
    Return 5–10 relevant suggestions for the next field to be filled.
    Respects context (e.g. filter domains by selected industry).
    """
    try:
        if next_field == "geography":
            return {"geography": GEOGRAPHY_SUGGESTIONS[:8]}

        if next_field == "industry":
            return {"industry": get_industries()[:10]}

        if next_field == "industry_domain":
            industry = context.get("industry")
            if industry:
                data = get_industry_domains_by_industry(industry)
                if data:
                    return {"industry_domain": data[:10]}
            # Fallback to all domains
            return {"industry_domain": get_industry_domains()[:10]}

        if next_field == "job_function":
            return {"job_function": get_job_functions()[:10]}

        if next_field == "job_level":
            return {"job_level": get_job_levels()[:10]}

        if next_field == "employee_size":
            return {"employee_size": get_employee_sizes()}

        if next_field == "revenue_range":
            return {"revenue_range": get_revenue_ranges()}

    except Exception as e:
        print(f"[SuggestionEngine Error] next_field={next_field}, error={e}")

    return {}