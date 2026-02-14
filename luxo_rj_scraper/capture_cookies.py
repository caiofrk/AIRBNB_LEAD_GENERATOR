"""
Script to capture logged-in cookies.
Usage:
1. Run this script.
2. A Chrome window will open.
3. Log in to Airbnb manually.
4. Once logged in, come back here and press Enter.
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
# Stealth arguments to bypass "This browser or app may not be secure"
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option('useAutomationExtension', False)
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

# Clear the navigator.webdriver flag
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

driver.get("https://www.airbnb.com.br/login")

input("\n>>> LOG IN MANUALLY in the browser window.\n>>> Once you are on the homepage/profile and logged in, press ENTER here to save cookies...")

cookies = driver.get_cookies()
with open("cookies_logged_in.json", "w") as f:
    json.dump(cookies, f)

print(f"✅ Successfully captured {len(cookies)} cookies to cookies_logged_in.json")
driver.quit()
