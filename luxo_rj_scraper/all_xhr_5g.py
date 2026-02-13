"""
Dump EVERY api/v3 response body on 5G Mobile Connection.
"""
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

LISTING_URL = "https://www.airbnb.com.br/rooms/1592936909077567519" # New target (Sandro)

print(f"=== Deep Interception on 5G Connection ===")
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Visiting: {LISTING_URL}")
driver.get(LISTING_URL)
time.sleep(20) # Give it plenty of time for all background fetches

logs = driver.get_log('performance')
captured_responses = []

print("Analyzing network logs...")
for entry in logs:
    try:
        msg = json.loads(entry['message'])['message']
        if msg['method'] == 'Network.responseReceived':
            url = msg['params']['response']['url']
            if 'api/v3' in url:
                req_id = msg['params']['requestId']
                # Get body via CDP
                try:
                    body_data = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                    body_text = body_data['body']
                    captured_responses.append({
                        "url": url,
                        "body": body_text[:1000] # store preview
                    })
                    
                    # Search logic
                    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', body_text)
                    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
                    
                    if real_emails:
                        print(f"--- 🎯 FOUND EMAILS in {url[:60]}... ---")
                        print(f"    Emails: {real_emails}")
                    
                    # Phone pattern (looking for numeric strings in JSON)
                    phones = re.findall(r'"\+?\d{10,15}"', body_text)
                    if phones:
                        print(f"--- 🎯 FOUND PHONES in {url[:60]}... ---")
                        print(f"    Phones: {phones}")
                        
                except:
                    pass
    except:
        pass

print("\nScan complete.")
driver.quit()
