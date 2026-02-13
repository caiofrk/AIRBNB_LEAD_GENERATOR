"""
Aggressive network scan of listing on 5G. 
Clicks 'Show More' sections to trigger all possible XHRs.
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

# Scroll to host section
try:
    host_sec = driver.find_element(By.XPATH, "//div[contains(@id, 'host-profile')] | //h2[contains(text(), 'Anfitri')]")
    driver.execute_script("arguments[0].scrollIntoView();", host_sec)
    print("Scrolled to Host section.")
    time.sleep(5)
except:
    print("Could not find Host section via XPath. Scrolling blindly...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(5)

# Try to find 'Mostrar mais' buttons and click them
buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Mostrar mais')]")
print(f"Clicking {len(buttons)} 'Mostrar mais' buttons...")
for btn in buttons:
    try:
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
    except:
        pass

time.sleep(10)

logs = driver.get_log('performance')
xhr_calls = []

for entry in logs:
    msg = json.loads(entry['message'])['message']
    if msg['method'] == 'Network.requestWillBeSent':
        url = msg['params']['request']['url']
        if 'api/v3' in url:
            xhr_calls.append(url)

print(f"Captured {len(xhr_calls)} API calls.")
with open("xhr_v3_listing.txt", "w") as f:
    for url in xhr_calls:
        f.write(url + "\n")

# Check if any specific HostProfile query appeared
for url in xhr_calls:
    if "Host" in url or "Profile" in url:
        print(f"Target XHR found: {url[:100]}...")

driver.quit()
