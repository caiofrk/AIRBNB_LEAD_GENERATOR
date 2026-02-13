"""
Check raw HTML for contact info using the mobile 5G connection.
"""
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

LISTING_ID = "1026988231993117868"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=opts)

print(f"Loading listing {LISTING_ID} on 5G...")
driver.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}")
time.sleep(10)

html = driver.page_source
with open("listing_5g.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Page HTML saved. Checking for patterns...")

emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html)
real_emails = [e for e in emails if 'airbnb' not in e.lower()]
phones = re.findall(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[\-\s]?\d{4}', html)

print(f"Emails found in HTML: {real_emails}")
print(f"Phones found in HTML: {phones[:5]}")

driver.quit()
