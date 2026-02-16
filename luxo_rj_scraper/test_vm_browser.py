import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def get_desktop_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    try:
        svc = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=svc, options=opts)
    except:
        return webdriver.Chrome(options=opts)

driver = get_desktop_driver()
try:
    url = "https://www.airbnb.com.br/s/Ipanema--Rio-de-Janeiro--RJ/homes?price_min=1000"
    print(f"Visiting {url}")
    driver.get(url)
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    listings = soup.select('div[data-testid="card-container"]')
    print(f"Found {len(listings)} listings")
    if len(listings) == 0:
        with open("dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Dumped HTML to dump.html")
finally:
    driver.quit()
