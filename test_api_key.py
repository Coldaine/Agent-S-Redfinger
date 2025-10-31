import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv('OPENAI_API_KEY')
if key:
    print(f"Key loaded: {key[:20]}...{key[-10:]}")
    print(f"Key length: {len(key)}")
else:
    print("Key: NONE")
    print("Key length: 0")

base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
url = base_url.rstrip('/') + '/chat/completions'

headers = {
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json'
}

payload = {
    'model': 'gpt-5',
    'messages': [{'role': 'user', 'content': 'Say hello'}],
    'max_completion_tokens': 10
}

print(f"\nCalling: {url}")
print(f"Model: gpt-5")

try:
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    print(f"\nStatus: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"\nError: {e}")
