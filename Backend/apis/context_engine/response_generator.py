# response_generator.py
from .openai_service import ask_gpt
def generate_human_response(user_input, context):
    prompt = f"""
You are a senior B2B strategist.

User input:
{user_input}

Context:
{context}

Respond conversationally.
Keep it concise.
Sound intelligent and human.
"""

    return ask_gpt(prompt)