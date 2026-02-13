"""
Get StaysPdpSections JSON on 5G using standard Desktop Chrome headers.
"""
import requests
import json
import base64
import re

LISTING_ID = "1592936909077567519"
API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
HASH = "f39436ef71149e853b9c01843700de06029ab1d55e8088d74a2629807428ac2c"

s = requests.Session()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
s.headers.update({'User-Agent': ua})

print("Getting CSRF...")
r = s.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")
csrf = re.search(r'"csrf_token":"(.*?)"', r.text)
token = csrf.group(1) if csrf else ""
print(f"Token: {token}")

b64_id = base64.b64encode(f"StayListing:{LISTING_ID}".encode()).decode()

variables = {
    "id": b64_id,
    "pdpSectionsRequest": {
        "adults": "1",
        "bypassTargetings": False,
        "layouts": ["SIDEBAR", "SINGLE_COLUMN"],
        "preview": False,
        "useDeviceWidth": False
    }
}

params = {
    'operationName': 'StaysPdpSections',
    'locale': 'pt',
    'currency': 'BRL',
    'variables': json.dumps(variables, separators=(',', ':')),
    'extensions': json.dumps({"persistedQuery":{"version":1,"sha256Hash":HASH}}, separators=(',', ':'))
}

api_headers = {
    'x-airbnb-api-key': API_KEY,
    'x-airbnb-graphql-request-priority': '0',
    'x-csrf-token': token,
    'Accept': 'application/json'
}

api_url = f"https://www.airbnb.com.br/api/v3/StaysPdpSections/{HASH}"

print(f"Requesting API v3 on 5G...")
resp = s.get(api_url, headers=api_headers, params=params)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    with open("sandro_sections_5g.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    raw = json.dumps(data)
    print(f"Size: {len(raw)}")
    
    # regex search for phone/email
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw)
    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
    phones = re.findall(r'"\d{10,15}"', raw)
    
    print(f"Emails: {real_emails}")
    print(f"Phones: {phones[:10]}")
    
    if '"host_profile"' in raw.lower():
        print("DETECTED 'host_profile' section!")
else:
    print(f"Error: {resp.status_code}")
