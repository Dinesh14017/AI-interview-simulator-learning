import requests
import json
import sys

URL = "http://localhost:8001/interview/start"
PAYLOAD = {
    "role": "software_engineer",
    "difficulty": "medium",
    "company": "Generic"
}

try:
    print(f"Sending POST request to {URL}...")
    response = requests.post(URL, json=PAYLOAD, timeout=60)
    
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2))
    except:
        print("Response Text:")
        print(response.text)

except Exception as e:
    print(f"Request failed: {e}")
