"""
Final Interception on Sandro José (Legacy ID).
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

LISTING_URL = "https://www.airbnb.com.br/rooms/42974021"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Loading {LISTING_URL} on 5G...")
driver.get(LISTING_URL)
time.sleep(15)

logs = driver.get_log('performance')
for entry in logs:
    try:
        msg = json.loads(entry['message'])['message']
        if msg['method'] == 'Network.responseReceived':
            url = msg['params']['response']['url']
            if 'StaysPdpSections' in url:
                req_id = msg['params']['requestId']
                try:
                    body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                    raw = body['body']
                    import re
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw)
                    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
                    phones = re.findall(r'"\+?\d{10,15}"', raw)
                    
                    if real_emails or phones:
                        print(f"🎯 FOUND DATA on {LISTING_URL}!")
                        print(f"Emails: {real_emails}")
                        print(f"Phones: {phones[:10]}")
                    else:
                        print(f"Checked {url[:40]}... No contact info found.")
                except:
                    pass
    except:
        pass

driver.quit()
