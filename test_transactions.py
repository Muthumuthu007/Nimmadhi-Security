import requests
import json

url = "http://localhost:8000/api/reports/transactions/"
response = requests.post(url, json={})

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total transactions: {len(data)}")
    if data:
        print(f"First transaction: {data[0]}")
else:
    print(f"Error: {response.text}")