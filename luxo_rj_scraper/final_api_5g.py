"""
Perfect Step 4 Implementation on 5G.
Uses exactly the headers and approach prescribed.
"""
import requests
import re
import json
import base64

API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
HASH = "f39436ef71149e853b9c01843700de06029ab1d55e8088d74a2629807428ac2c"
LISTING_ID = "1026988231993117868"

s = requests.Session()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
s.headers.update({
    'User-Agent': ua,
    'Accept': 'application/json',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': f'https://www.airbnb.com.br/rooms/{LISTING_ID}',
})

print("Warming up session on 5G...")
r1 = s.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}", timeout=20)

# Extract CSRF token from cookies or text
token = s.cookies.get('csrf_token')
if not token:
    # Try regex on HTML
    match = re.search(r'"csrf_token":"(.*?)"', r1.text)
    if match: token = match.group(1)

print(f"Token: {token}")

# Setup Variables
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
extensions = {"persistedQuery":{"version":1,"sha256Hash":HASH}}

# Headers from Guide
headers = {
    'x-airbnb-api-key': API_KEY,
    'x-airbnb-graphql-request-priority': '0',
    'x-csrf-token': token,
    'User-Agent': ua
}

api_url = f"https://www.airbnb.com.br/api/v3/StaysPdpSections/{HASH}"
params = {
    'operationName': 'StaysPdpSections',
    'locale': 'pt',
    'currency': 'BRL',
    'variables': json.dumps(variables, separators=(',', ':')),
    'extensions': json.dumps(extensions, separators=(',', ':'))
}

print("Making DIRECT API call...")
resp = s.get(api_url, headers=headers, params=params)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    raw = json.dumps(data)
    print(f"Payload Size: {len(raw)}")
    
    with open("final_5g_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    # SEARCH FOR CONTACT
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw)
    phones = re.findall(r'"\+?\d{10,15}"', raw)
    print(f"Emails found: {emails}")
    print(f"Phones found: {phones}")
    
    if '"host_profile"' in raw.lower():
        print("--- 🎯 HOST PROFILE SECTION DETECTED! ---")
else:
    print(f"Error: {resp.text[:500]}")
