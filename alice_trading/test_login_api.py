import requests
import json

url = "http://localhost:8001/api/v1/auth/login"
payload = {
    "user_id": "nemturivishnuvardan@gmail.com",
    "api_key": "Password@123"
}
headers = {
    "Content-Type": "application/json"
}

try:
    print(f"Sending login request to {url}...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
