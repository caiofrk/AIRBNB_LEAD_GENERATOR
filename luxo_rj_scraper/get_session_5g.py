"""
Get real CSRF token from Selenium on 5G.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=opts)
driver.get("https://www.airbnb.com.br/rooms/1026988231993117868")
time.sleep(10)

# Extract CSRF and other relevant headers
csrf = driver.execute_script("return (window && window._csrf_token) || (window.AirbnbBootstrap && window.AirbnbBootstrap.csrf_token);")
print(f"CSRF extracted: {csrf}")

# Get all cookies
cookies = driver.get_cookies()
print(f"Cookies captured: {len(cookies)}")

with open("session_5g.json", "w") as f:
    json.dump({"csrf": csrf, "cookies": cookies}, f)

driver.quit()
