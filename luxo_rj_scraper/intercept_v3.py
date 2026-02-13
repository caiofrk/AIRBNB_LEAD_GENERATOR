"""
Final Interception Attempt using User's Mobile IP + Googlebot Spoofing.
"""
import json
import re
import time
import requests
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

LISTING_ID = "1026988231993117868" 

print(f"=== Starting Interception Attempt: 5G + Googlebot UA ===")

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
# SPOOF GOOGLEBOT UA
opts.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Navigating to listing with Googlebot UA: {LISTING_ID}...")
driver.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")
time.sleep(15)

logs = driver.get_log('performance')
target_request_id = None

for entry in logs:
    msg = json.loads(entry['message'])['message']
    if msg['method'] == 'Network.responseReceived':
        url = msg['params']['response']['url']
        if 'StaysPdpSections' in url:
            target_request_id = msg['params']['requestId']
            print(f"Found target XHR! requestId: {target_request_id}")
            break

if target_request_id:
    try:
        body_data = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': target_request_id})
        json_content = json.loads(body_data['body'])
        
        raw_payload = json.dumps(json_content)
        emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw_payload)
        real_emails = [e for e in emails if 'airbnb' not in e.lower()]
        phones = re.findall(r'"\+?\d{10,15}"', raw_payload)
        
        print(f"\nEmails found: {real_emails}")
        print(f"Phones found: {phones}")

        # Check for @type host_profile mentioned by user
        if '"host_profile"' in raw_payload.lower():
            print("Detected 'host_profile' in payload!")

    except Exception as e:
        print(f"Failed to get response body: {e}")
else:
    print("StaysPdpSections XHR not detected.")

driver.quit()
