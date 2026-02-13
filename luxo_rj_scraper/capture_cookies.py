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

print("Starting Chrome... Please log in to Airbnb in the window that opens.")

opts = Options()
# DO NOT USE HEADLESS - User needs to see and interact
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("window-size=1200,800")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
driver.get("https://www.airbnb.com.br/login")

input("\n>>> LOG IN MANUALLY in the browser window.\n>>> Once you are on the homepage/profile and logged in, press ENTER here to save cookies...")

cookies = driver.get_cookies()
with open("cookies_logged_in.json", "w") as f:
    json.dump(cookies, f)

print(f"✅ Successfully captured {len(cookies)} cookies to cookies_logged_in.json")
driver.quit()
