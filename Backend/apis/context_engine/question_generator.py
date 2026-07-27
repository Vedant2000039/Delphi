#question_generator.py
REQUIRED_FIELDS = [
    "industry",
    "geography",
    "employee_size",
    "revenue_range",
    "job_function",
    "job_level"
]

QUESTION_MAP = {

    "industry":
        "Which industry are you targeting?",

    "geography":
        "Which geography would you like to target?",

    "job_function":
        "Which department or job function are you targeting?",

    "job_level":
        "What seniority level should we focus on?",

    "employee_size":
        "What employee size range should we target?",

    "revenue_range":
        "What company revenue range should we focus on?"
}

def get_missing_fields(context):
    return [f for f in REQUIRED_FIELDS if f not in context]

def generate_question(context):
    missing = get_missing_fields(context)
    if not missing:
        return None
    return QUESTION_MAP[missing[0]]