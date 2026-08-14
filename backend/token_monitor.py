import os
from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------------------
# Load .env
# --------------------------------------------------
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=api_key)


# --------------------------------------------------
# OpenAI API request with raw response
# --------------------------------------------------
raw_response = client.chat.completions.with_raw_response.create(
    model="gpt-4.1-mini",
    messages=[
        {
            "role": "user",
            "content": "Hello, give me a short response."
        }
    ]
)

# Convert raw response into normal ChatCompletion object
response = raw_response.parse()


# --------------------------------------------------
# Token usage
# --------------------------------------------------
usage = response.usage

input_tokens = usage.prompt_tokens
output_tokens = usage.completion_tokens
total_tokens = usage.total_tokens


# --------------------------------------------------
# Rate-limit headers
# --------------------------------------------------
headers = raw_response.headers

remaining_requests = headers.get(
    "x-ratelimit-remaining-requests"
)

remaining_tokens = headers.get(
    "x-ratelimit-remaining-tokens"
)

request_limit = headers.get(
    "x-ratelimit-limit-requests"
)

token_limit = headers.get(
    "x-ratelimit-limit-tokens"
)


# --------------------------------------------------
# Display
# --------------------------------------------------
print()
print("=" * 55)
print("              OPENAI TOKEN MONITOR")
print("=" * 55)

print(f"Model                : {response.model}")

print()
print("CURRENT REQUEST")
print("-" * 55)
print(f"Input tokens         : {input_tokens}")
print(f"Output tokens        : {output_tokens}")
print(f"Total tokens used    : {total_tokens}")

print()
print("RATE LIMIT")
print("-" * 55)

print(
    f"Token limit          : "
    f"{token_limit if token_limit else 'Not available'}"
)

print(
    f"Tokens remaining     : "
    f"{remaining_tokens if remaining_tokens else 'Not available'}"
)

print(
    f"Request limit        : "
    f"{request_limit if request_limit else 'Not available'}"
)

print(
    f"Requests remaining   : "
    f"{remaining_requests if remaining_requests else 'Not available'}"
)

print()
print("=" * 55)

print()
print("MODEL RESPONSE")
print("-" * 55)
print(response.choices[0].message.content)

print()