import os
import time
import random
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API")

# Initialize Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Warning: Supabase connection failed. check .env. ({e})")
    supabase = None

def get_lux_score(price, title, photos_count, badges=None):
    score = 0
    if price >= 1000: score += 15
    if price >= 3000: score += 15
    if price >= 5000: score += 10
    
    keywords = ['luxo', 'luxury', 'vista mar', 'ocean view', 'cobertura', 'penthouse', 'design', 'exclusivo']
    lower_title = title.lower()
    for kw in keywords:
        if kw in lower_title:
            score += 5
            
    if badges:
        if "Luxe" in badges: score += 30
        if "Plus" in badges: score += 15
    
    return min(score, 100)

def deep_analyze_listing(driver, lead_id, url):
    """Deeply crawls a single listing to extract detailed features and reviews."""
    print(f"    [Deep Analysis] Processing: {url[:50]}...")
    try:
        driver.get(url)
        time.sleep(random.uniform(5, 7))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text().lower()
        updates = {"intelligence_status": "ready"}

        # 1. Scrape Description (Look for specialized features)
        desc_el = soup.select_one('div[data-section-id="DESCRIPTION_DEFAULT"], div[data-testid="pdp-description-content"]')
        description = desc_el.get_text(strip=True) if desc_el else ""
        updates['descricao'] = description
        
        # 2. Extract Maintenance Hooks (Technical keywords)
        maintenance_map = {
            'Superfícies Nobres (Mármore/Vidro)': ['mármore', 'marble', 'vidro', 'glass', 'madeira maciça'],
            'Piscina/Jacuzzi': ['piscina', 'pool', 'jacuzzi', 'hidromassagem', 'hot tub'],
            'Automação/Eletrônicos': ['automatizada', 'alexa', 'voice command', 'cinema', 'projetor', 'smart'],
            'Máquinas de Café (Nespresso/Etc)': ['nespresso', 'espresso', 'cafeteira']
        }
        found_maintenance = []
        for label, kws in maintenance_map.items():
            if any(kw in page_text for kw in kws):
                found_maintenance.append(label)
        updates['maintenance_items'] = found_maintenance

        # 3. Cleanliness Gap (Scanning Reviews)
        flags = ['poeira', 'sujo', 'limpeza', 'dust', 'dirty', 'mancha', 'odor', 'baseboard', 'rodapé', 'fingerprint']
        gap_mentions = []
        review_els = soup.select('div[data-testid="pdp-reviews-modal-scrollable-container"] span, span.ll4r2nl')
        for r in review_els:
            txt = r.get_text().lower()
            if any(f in txt for f in flags):
                gap_mentions.append(txt[:100].strip())
        
        if gap_mentions:
            updates['cleanliness_gap'] = " | ".join(list(set(gap_mentions))[:2])

        # 4. Host Info
        host_profile = soup.select_one('div[data-testid="pdp-host-profile-section"]')
        if host_profile:
            txt = host_profile.get_text().lower()
            m = re.search(r'(\d+)\s+anúncios', txt)
            updates['host_portfolio_size'] = int(m.group(1)) if m else 1

        if supabase:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
        print(f"      [DONE] Intelligence generated for lead {lead_id}.")
        
    except Exception as e:
        print(f"    [!] Deep Analysis Error: {e}")
        if supabase:
            supabase.table("leads").update({"intelligence_status": "none"}).eq("id", lead_id).execute()

def scrape_main_leads():
    """Fast scrape to populate the database with new opportunities."""
    print("--- Running Main Scraper (Fast Phase) ---")
    neighborhoods = [
         "Ipanema", "Leblon", "Barra da Tijuca", "Joá", "São Conrado", "Lagoa", "Copacabana", 
         "Itanhangá", "Guaratiba", "Botafogo", "Vargem Grande", "Vargem Pequena", "Ilha de Guaratiba"
    ]
    checkin, checkout, num_nights = "2026-06-11", "2026-06-13", 2
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        for loc in neighborhoods:
            print(f" 🔍 Neighborhood: {loc}")
            url = f"https://www.airbnb.com.br/s/{loc}--Rio-de-Janeiro--RJ/homes?price_min=1000&room_types%5B%5D=Entire+home%2Fapt&checkin={checkin}&checkout={checkout}"
            driver.get(url)
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.select('div[data-testid="card-container"]')
            
            for item in listings[:20]:
                try:
                    title_el = item.select_one('div[data-testid="listing-card-title"]')
                    title = title_el.get_text(strip=True) if title_el else "Luxury Property"
                    
                    price_el = item.select_one('div[data-testid="price-availability-row"] > div > span:last-child')
                    price = 1000
                    if price_el:
                        digits = ''.join(filter(str.isdigit, price_el.get_text().split(',')[0].replace('.', '')))
                        price = int(int(digits) / num_nights) if digits else 1000

                    link_el = item.find('a', href=True)
                    link = "https://airbnb.com.br" + link_el['href'].split('?')[0] if link_el else ""
                    
                    if supabase and link:
                        exists = supabase.table("leads").select("id").eq("link_imovel", link).execute()
                        if not exists.data:
                            lead = {
                                "titulo": title, "link_imovel": link, "preco_noite": price, 
                                "bairro": loc, "lux_score": get_lux_score(price, title, 30),
                                "intelligence_status": "none"
                            }
                            supabase.table("leads").insert(lead).execute()
                            print(f"    [+] New Lead: {title[:20]}")
                except: continue
    finally:
        driver.quit()

def start_watcher():
    """Stays active and waits for requests from the app."""
    print("\n🚀 [WATCHER] Intelligence Engine is ACTIVE.")
    print("Keep this terminal open. Requests from your phone will appear here instantly.\n")
    
    while True:
        try:
            # Check for pending intelligence requests
            pending = supabase.table("leads").select("id, link_imovel").eq("intelligence_status", "pending").execute()
            
            if pending.data:
                print(f"🔔 Request Detected! Processing {len(pending.data)} lead(s)...")
                options = Options()
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                
                try:
                    for p in pending.data:
                        deep_analyze_listing(driver, p['id'], p['link_imovel'])
                finally:
                    driver.quit()
                    print("✅ Processing complete. Waiting for new requests...")
            
        except Exception as e:
            print(f"Watcher error: {e}")
            
        time.sleep(5) # Check every 5 seconds for instant feedback

if __name__ == "__main__":
    import sys
    
    # Check if we want to do a fresh search first
    if "search" in sys.argv:
        scrape_main_leads()
        
    if "deep" in sys.argv:
        # Single-run mode for GitHub Actions: process pending and exit
        print("--- Running Deep Intelligence (Single Run) ---")
        pending = supabase.table("leads").select("id, link_imovel").eq("intelligence_status", "pending").execute()
        if pending.data:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            try:
                for p in pending.data:
                    deep_analyze_listing(driver, p['id'], p['link_imovel'])
            finally:
                driver.quit()
        else:
            print("No pending requests.")
    else:
        # Continuous watcher mode for local use
        start_watcher()
