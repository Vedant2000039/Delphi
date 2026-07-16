# # # openai_service.py
# # from openai import OpenAI
# # from .config import OPENAI_API_KEY

# # client = OpenAI(api_key=OPENAI_API_KEY)


# # def ask_gpt(prompt, temperature=0.7):

# #     response = client.responses.create(
# #         model="gpt-4.1-mini",
# #         input=prompt,
# #         temperature=temperature,
# #         max_output_tokens=500
# #     )

# #     return response.output_text.strip()


# # openai_service.py
# import os
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# def ask_gpt(prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
#     """
#     Call GPT-4.1-mini with a given prompt.
#     Returns the response text, or empty string on failure.
#     """
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=temperature,
#             max_tokens=max_tokens
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"[OpenAI Error] {e}")
#         return ""



# openai_service.py
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

_quota_exhausted_until = 0  # module-level cooldown timestamp

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_gpt(prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """
    Call GPT-4.1-mini with a given prompt.
    Returns the response text, or empty string on failure.
    """
    global _quota_exhausted_until

    if time.time() < _quota_exhausted_until:
        # Skip the call entirely while quota is known to be exhausted
        return ""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            _quota_exhausted_until = time.time() + 300  # back off 5 minutes
        print(f"[OpenAI Error] {e}")
        return ""