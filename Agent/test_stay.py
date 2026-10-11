import os
import requests
from dotenv import load_dotenv

load_dotenv()

hotels_api_key = os.getenv("HOTELS_API_KEY")

if not hotels_api_key:
    raise ValueError("Hotels API key not set")

url = "https://api.stayingapi.com/v1/search"

params = {
    "location": "Split, HR",
    "checkIn": "2026-10-20",
    "checkOut": "2026-10-23",
    "platforms": "booking",
    "limit": 5,
}

headers = {
    "Authorization": f"Bearer {hotels_api_key}",
}

response = requests.get(url, headers=headers, params=params, timeout=30,)

print(response.status_code)
print(response.text)

response.raise_for_status()