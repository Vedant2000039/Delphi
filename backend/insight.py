import requests

resp = requests.post(
    "https://api.explorium.ai/v1/businesses/match",
    headers={"api_key": "YOUR_API_KEY"},
    json={"businesses_to_match": [{"name": "Explorium", "domain": "explorium.ai"}]},
)
print(resp.json())