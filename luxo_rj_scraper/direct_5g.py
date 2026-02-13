"""
Final Implementation of Strategy 4: Direct Signed Request on 5G.
"""
import requests
import re
import json
import base64

LISTING_ID = "1026988231993117868"
API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"

s = requests.Session()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
s.headers.update({
    'User-Agent': ua,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
})

print("Fetching initial page for cookies and CSRF...")
r = s.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")

# Extract CSRF
csrf_token = None
# Try cookie
if 'csrf_token' in s.cookies:
    csrf_token = s.cookies['csrf_token']
# Try HTML
if not csrf_token:
    m = re.search(r'"csrf_token":"(.*?)"', r.text)
    if m:
        csrf_token = m.group(1)

print(f"CSRF Token: {csrf_token}")

# Target Section Query (from previous log capture)
# Note: Hash might need to be exact. I'll use the one from Step 3395 (truncated there, I'll find it in my previous dump if I can or use the one I know)
HASH = "f39436ef71149e853b9c01843700de06029ab1d55e8088d74a2629807428ac2c"

b64_id = base64.b64encode(f"StayListing:{LISTING_ID}".encode()).decode()

variables = {
    "id": b64_id,
    "pdpSectionsRequest": {
        "adults": "1",
        "bypassTargetings": False,
        "categoryTag": None,
        "causeId": None,
        "children": None,
        "disasterId": None,
        "discountedGuestFeeVersion": None,
        "displayExtensions": None,
        "federatedSearchId": None,
        "forceBoostPriorityMessageType": None,
        "infants": None,
        "interactionType": None,
        "layouts": ["SIDEBAR", "SINGLE_COLUMN"],
        "pdpTypeOverride": None,
        "photoId": None,
        "preview": False,
        "previousPageSectionName": None,
        "promotionUuid": None,
        "relaxedAmenityIds": None,
        "searchId": None,
        "sectionIds": None,
        "sharerId": None,
        "state": None,
        "translateUgc": None,
        "useDeviceWidth": False
    }
}

extensions = {
    "persistedQuery": {
        "version": 1,
        "sha256Hash": HASH
    }
}

# The headers user said are mandatory
api_headers = {
    'x-airbnb-api-key': API_KEY,
    'x-airbnb-graphql-request-priority': '0',
    'x-csrf-token': csrf_token,
    'User-Agent': ua,
    'Referer': f'https://www.airbnb.com.br/rooms/{LISTING_ID}',
    'Accept': 'application/json'
}

api_url = f"https://www.airbnb.com.br/api/v3/StaysPdpSections/{HASH}"
params = {
    'operationName': 'StaysPdpSections',
    'locale': 'pt',
    'currency': 'BRL',
    'variables': json.dumps(variables, separators=(',', ':')),
    'extensions': json.dumps(extensions, separators=(',', ':'))
}

print(f"Calling API with Mobile IP + headers...")
resp = s.get(api_url, headers=api_headers, params=params)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    raw = json.dumps(data)
    
    with open("direct_5g_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Response size: {len(raw)}")
    
    # Check for contacts
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw)
    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
    phones = re.findall(r'"\+?\d{10,15}"', raw)
    
    print(f"Emails: {real_emails}")
    print(f"Phones: {phones}")
    
    if 'phone' in raw.lower() or 'email' in raw.lower():
        print("Detected 'phone' or 'email' keys!")
else:
    print(f"Error: {resp.text[:500]}")
