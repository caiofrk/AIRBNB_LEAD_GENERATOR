"""
Try Mobile User-Agent on 5G to see if it bypasses sanitization.
"""
import requests
import re
import json

LISTING_ID = "1592936909077567519"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

s = requests.Session()
s.headers.update({'User-Agent': UA})

print(f"Requesting listing as iPhone on 5G...")
r = s.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")
print(f"Status: {r.status_code}")

# Extract Token - looking for it anywhere in the text
token = None
m = re.search(r'"csrf_token":"(.*?)"', r.text)
if m:
    token = m.group(1)
else:
    # Try another pattern
    m = re.search(r'csrf_token&quot;:&quot;(.*?)&quot;', r.text)
    if m:
        token = m.group(1)

print(f"Token Found: {token}")

if r.status_code == 200:
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', r.text)
    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
    print(f"Emails in Mobile HTML: {real_emails}")
    
    # Try the API with the token
    if token:
        print("Trying API v3 with Mobile Token...")
        # ... logic for API call ...
        pass
