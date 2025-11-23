import requests
import json

# Test the get_today_logs endpoint
url = "http://localhost:8000/reports/logs/today/"
payload = {"limit": 10}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")