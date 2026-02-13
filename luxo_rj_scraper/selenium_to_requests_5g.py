"""
Sync Selenium to Requests on 5G to get the real non-sanitized API data.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import json
import base64
import time
import re

LISTING_ID = "1026988231993117868"
API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
HASH = "f39436ef71149e853b9c01843700de06029ab1d55e8088d74a2629807428ac2c"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
opts.add_argument(f"user-agent={ua}")

print("Starting Selenium to warm up session...")
driver = webdriver.Chrome(options=opts)
driver.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")
time.sleep(15)

# Extract CSRF via JS
csrf = driver.execute_script("return (window && window._csrf_token) || (window.AirbnbBootstrap && window.AirbnbBootstrap.csrf_token);")
if not csrf:
    # Try searching the page source for "csrf_token"
    m = re.search(r'"csrf_token":"(.*?)"', driver.page_source)
    if m: csrf = m.group(1)

print(f"Captured CSRF: {csrf}")

# Sync Cookies
s = requests.Session()
for cookie in driver.get_cookies():
    s.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

driver.quit()

if csrf:
    print("Making Request with Session + CSRF + 5G...")
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
    
    headers = {
        'x-airbnb-api-key': API_KEY,
        'x-airbnb-graphql-request-priority': '0',
        'x-csrf-token': csrf,
        'User-Agent': ua,
        'Accept': 'application/json'
    }
    
    params = {
        'operationName': 'StaysPdpSections',
        'locale': 'pt',
        'currency': 'BRL',
        'variables': json.dumps(variables, separators=(',', ':')),
        'extensions': json.dumps({"persistedQuery":{"version":1,"sha256Hash":HASH}}, separators=(',', ':'))
    }
    
    resp = s.get(f"https://www.airbnb.com.br/api/v3/StaysPdpSections/{HASH}", headers=headers, params=params)
    print(f"API Status: {resp.status_code}")
    
    if resp.status_code == 200:
        raw = resp.text
        print(f"Payload Size: {len(raw)}")
        
        # SEARCH FOR CONTACT
        emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw)
        real_emails = [e for e in emails if 'airbnb' not in e.lower()]
        phones = re.findall(r'"\+?\d{10,15}"', raw)
        
        print(f"Emails: {real_emails}")
        print(f"Phones: {phones[:10]}")
    else:
        print(f"Error: {resp.text[:500]}")
else:
    print("Failed to capture CSRF.")
