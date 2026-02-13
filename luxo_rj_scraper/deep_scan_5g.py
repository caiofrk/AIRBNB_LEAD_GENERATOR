"""
Search performance logs for ALL relevant XHR calls, not just StaysPdpSections.
Look for 'host', 'profile', 'contact', 'user'.
"""
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

LISTING_ID = "1026988231993117868"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Deep scanning network for {LISTING_ID}...")
driver.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")

# Scroll a bit to trigger more fetches
driver.execute_script("window.scrollTo(0, 1000);")
time.sleep(5)
driver.execute_script("window.scrollTo(0, 3000);")
time.sleep(10)

logs = driver.get_log('performance')
xhr_calls = []

for entry in logs:
    msg = json.loads(entry['message'])['message']
    if msg['method'] == 'Network.requestWillBeSent':
        url = msg['params']['request']['url']
        if 'api/v3' in url:
            method = msg['params']['request']['method']
            xhr_calls.append(f"{method}: {url}")

print(f"Found {len(xhr_calls)} API calls. Relevant ones:")
for call in xhr_calls:
    if any(x in call.lower() for x in ['host', 'section', 'profile', 'user', 'contact']):
        print(f"  {call[:150]}...")

driver.quit()
