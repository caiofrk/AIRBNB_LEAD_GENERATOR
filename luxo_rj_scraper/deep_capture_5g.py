"""
Deep capture of all large API responses on 5G.
We are looking for the host contact info guide.
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

LISTING_URL = "https://www.airbnb.com.br/rooms/1026988231993117868"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Loading {LISTING_URL} and scrolling slowly to bottom...")
driver.get(LISTING_URL)
time.sleep(5)

for i in range(10):
    driver.execute_script(f"window.scrollTo(0, {i * 1000});")
    time.sleep(2)

print("Capturing all XHR bodies...")
logs = driver.get_log('performance')
api_responses = []

for entry in logs:
    try:
        msg = json.loads(entry['message'])['message']
        if msg['method'] == 'Network.responseReceived':
            url = msg['params']['response']['url']
            if 'api/v3' in url:
                req_id = msg['params']['requestId']
                try:
                    body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                    size = len(body['body'])
                    print(f"Captured {url[:60]}... (Size: {size})")
                    
                    # Search for clues
                    if "phone" in body['body'].lower() or "email" in body['body'].lower() or "anfitri" in body['body'].lower():
                        print(f"  🎯 Found keyword in {url[:40]}!")
                        if size > 1000:
                            filename = f"resp_{req_id}.json"
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(body['body'])
                            print(f"  Saved as {filename}")

                except:
                    pass
    except:
        pass

driver.quit()
