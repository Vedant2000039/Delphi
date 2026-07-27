# conversation_planner.py
REQUIRED_FIELDS = [
    "geography",        # 1st
    "industry",         # 2nd
    "job_function",
    "job_level",
    "employee_size",
    "revenue_range"
]

QUESTION_BANK = {

    "industry":
        "Which industry are you targeting?",

    "industry_domain":
        "Which domain or sector does your product belong to?",

    "geography":
        "Which geography would you like to target?",

    "job_function":
        "Which department or job function are you targeting?",

    "job_level":
        "What seniority level should we focus on?",

    "employee_size":
        "What employee size are you targeting?",

    "revenue_range":
        "What revenue range should the companies have?"
}


def get_missing_fields(context):

    missing = []

    for field in REQUIRED_FIELDS:
        if not context.get(field):
            missing.append(field)

    return missing

def generate_next_question(
    context,
    suggestions
):

    missing = get_missing_fields(context)

    if not missing:
        return None

    field = missing[0]

    return QUESTION_BANK[field]