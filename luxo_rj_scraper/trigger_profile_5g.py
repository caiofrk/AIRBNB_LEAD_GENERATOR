"""
Trigger Host Profile XHR on 5G.
Clicks the host avatar to force the profile data to load.
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

LISTING_URL = "https://www.airbnb.com.br/rooms/1026988231993117868"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Loading {LISTING_URL} on 5G...")
driver.get(LISTING_URL)
time.sleep(10)

# Find and click host avatar or name
try:
    # Multiple selectors for host link
    host_link = driver.find_element(By.XPATH, "//a[contains(@href, '/users/show/')]")
    print(f"Clicking host link: {host_link.get_attribute('href')}")
    driver.execute_script("arguments[0].click();", host_link)
    time.sleep(10)
except Exception as e:
    print(f"Could not click host link: {e}")

logs = driver.get_log('performance')
for entry in logs:
    msg = json.loads(entry['message'])['message']
    if msg['method'] == 'Network.responseReceived':
        url = msg['params']['response']['url']
        if 'api/v3' in url:
            req_id = msg['params']['requestId']
            try:
                body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                text = body['body']
                if "phone" in text.lower() or "email" in text.lower():
                    print(f"🎯 FOUND DATA in {url[:60]}")
                    with open("profile_click_resp.json", "w", encoding="utf-8") as f:
                         f.write(text)
            except:
                pass

driver.quit()
