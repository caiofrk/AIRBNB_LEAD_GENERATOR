"""
Force capture of CSRF from Selenium on 5G.
Searches inside script tags for the token.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re
import json

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=opts)
driver.get("https://www.airbnb.com.br/rooms/1026988231993117868")
time.sleep(15)

html = driver.page_source
# Find the bootstrap script
m = re.search(r'\{&quot;csrf_token&quot;:&quot;(.*?)&quot;\}', html)
token = m.group(1) if m else "Not Found"

# Try another pattern
if token == "Not Found":
    m = re.search(r'"csrf_token":"(.*?)"', html)
    if m: token = m.group(1)

print(f"FORCED_TOKEN: {token}")

# Save session for the API script
cookies = driver.get_cookies()
with open("session_capture.json", "w") as f:
    json.dump({"csrf": token, "cookies": cookies}, f)

driver.quit()
