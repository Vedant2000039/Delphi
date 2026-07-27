# prompt_builder.py
import re
def _extract_limit(user_query: str) -> int:
    """Extract numeric limit from phrases like 'top 10', 'show 20'."""
    if not user_query:
        return 10
    patterns = [r"top\s+(\d+)", r"limit\s+(\d+)", r"show\s+(\d+)", r"get\s+(\d+)"]
    for pattern in patterns:
        match = re.search(pattern, user_query.lower())
        if match:
            return int(match.group(1))
    return 10


def build_cortex_prompt(context: dict, user_query: str = "") -> str:
    """
    Build a natural language prompt for Snowflake Cortex Analyst
    based on collected context.
    """
    parts = []
    limit = _extract_limit(user_query)

    if context.get("geography"):
        parts.append(f"geography is {context['geography']}")

    if context.get("industry"):
        parts.append(f"industry is {context['industry']}")

    # if context.get("industry_domain"):
    #     parts.append(f"sector is {context['industry_domain']}")

    # if context.get("job_function"):
    #     parts.append(f"job function is {context['job_function']}")

    # if context.get("job_level"):
    #     parts.append(f"job level is {context['job_level']}")

    # if context.get("employee_size"):
    #     parts.append(f"employee size is {context['employee_size']}")

    # if context.get("revenue_range"):
    #     parts.append(f"revenue range is {context['revenue_range']}")

    if not parts:
        return "Give me leads details from all countries  limit 10"

    criteria = " and ".join(parts)
    prompt = f"Give me leads details where {criteria}  limit {limit}"

    print(f"[CortexPrompt] {prompt}")
    return prompt