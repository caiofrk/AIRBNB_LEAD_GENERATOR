"""
Logged-in Interception using the captured cookies.
"""
import json
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

LISTING_ID = "1026988231993117868"
COOKIE_FILE = "cookies_logged_in.json"

if not os.path.exists(COOKIE_FILE):
    print(f"Error: {COOKIE_FILE} not found. Please run capture_cookies.py first.")
    exit(1)

print(f"=== Starting Logged-in Interception (5G) ===")

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
driver.execute_cdp_cmd("Network.enable", {})

# Set cookies
driver.get("https://www.airbnb.com.br/robots.txt")
with open(COOKIE_FILE, "r") as f:
    cookies = json.load(f)
    for c in cookies:
        # Compatibility fix for selenium cookie format
        if 'expiry' in c: c['expiry'] = int(c['expiry'])
        driver.add_cookie(c)

print(f"Navigating to listing as logged-in user: {LISTING_ID}...")
driver.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")
time.sleep(15)

# Intercept Logic
logs = driver.get_log('performance')
found_target = False

for entry in logs:
    try:
        msg = json.loads(entry['message'])['message']
        if msg['method'] == 'Network.responseReceived':
            url = msg['params']['response']['url']
            if 'StaysPdpSections' in url:
                req_id = msg['params']['requestId']
                body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                raw = body['body']
                
                print(f"--- Captured StaysPdpSections (Logged-in)! Size: {len(raw)} ---")
                with open("logged_in_pdp.json", "w", encoding="utf-8") as f:
                    f.write(raw)
                
                # Search for data
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw)
                real_emails = [e for e in emails if 'airbnb' not in e.lower()]
                phones = re.findall(r'"\+?\d{10,15}"', raw)
                
                print(f"Emails: {real_emails}")
                print(f"Phones: {phones[:10]}")
                
                if 'phone' in raw.lower() or 'email' in raw.lower():
                    print("🎯 Found keyword 'phone' or 'email' in payload!")
                
                found_target = True
                break
    except:
        pass

if not found_target:
    print("Failed to find the target XHR call.")

driver.quit()
