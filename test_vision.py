import os
import json
import requests
import base64
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

# Create a simple test image
img = Image.new('RGB', (100, 100), color='white')
buf = io.BytesIO()
img.save(buf, format='PNG')
png_bytes = buf.getvalue()
b64_img = "data:image/png;base64," + base64.b64encode(png_bytes).decode('ascii')

key = os.getenv('OPENAI_API_KEY')
url = 'https://api.openai.com/v1/chat/completions'

headers = {
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json'
}

payload = {
    'model': 'gpt-5',
    'messages': [
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'What do you see? Reply with just a few words.'},
                {'type': 'image_url', 'image_url': {'url': b64_img}}
            ]
        }
    ],
    'max_completion_tokens': 500
}

print(f"Calling: {url}")
print(f"Image size: {len(b64_img)} chars")

r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
print(f"\nStatus: {r.status_code}")
data = r.json()
print(f"Response:\n{json.dumps(data, indent=2)}")

if r.status_code == 200:
    content = data['choices'][0]['message'].get('content')
    print(f"\n Content: {repr(content)}")
