"""
Check Profile Page XHRs on 5G.
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

HOST_ID = "92284964"
url = f"https://www.airbnb.com.br/users/show/{HOST_ID}"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=opts)
driver.execute_cdp_cmd("Network.enable", {})

print(f"Visiting Profile: {url} on 5G...")
driver.get(url)
time.sleep(15)

logs = driver.get_log('performance')
for entry in logs:
    try:
        msg = json.loads(entry['message'])['message']
        if msg['method'] == 'Network.responseReceived':
            url_xhr = msg['params']['response']['url']
            if 'api/v3' in url_xhr:
                req_id = msg['params']['requestId']
                try:
                    body_data = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                    body_text = body_data['body']
                    size = len(body_text)
                    print(f"XHR: {url_xhr[:60]}... (Size: {size})")
                    
                    if "phone" in body_text.lower() or "email" in body_text.lower() or "anfitri" in body_text.lower():
                        print(f"  🎯 FOUND CLUES in {url_xhr[:40]}!")
                        import re
                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', body_text)
                        real_emails = [e for e in emails if 'airbnb' not in e.lower()]
                        if real_emails: print(f"    Emails: {real_emails}")
                except:
                    pass
    except:
        pass

driver.quit()
