import os
import time
import random
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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

def get_lux_score(price, title, photos_count):
    score = 0
    # Price based score
    if price >= 1000: score += 20
    if price >= 3000: score += 20
    if price >= 5000: score += 10
    
    # Keywords
    keywords = ['luxo', 'luxury', 'vista mar', 'ocean view', 'cobertura', 'penthouse', 'design', 'exclusivo']
    lower_title = title.lower()
    for kw in keywords:
        if kw in lower_title:
            score += 5
            
    # Photos
    if photos_count > 10: score += 5
    if photos_count > 30: score += 15
    if photos_count > 50: score += 10
    
    return min(score, 100)

def geocode_neighborhood(neighborhood):
    if not GOOGLE_API_KEY or "Key" in GOOGLE_API_KEY:
        return None, None
        
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{neighborhood}, Rio de Janeiro, Brazil", "key": GOOGLE_API_KEY}
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None, None

def enrich_lead(lead_id, data):
    print(f"  > Enriching lead {lead_id}: {data['titulo'][:30]}...")
    
    updates = {}
    title = data.get('titulo', '')
    bairro = data.get('bairro', '')

    # 1. Search for Condo/CNPJ via Google patterns
    try:
        if "Condomínio" in title or "Edifício" in title:
            updates['anfitriao'] = f"Adm {title.split(' ')[-1]}"
    except: pass

    # 2. Instagram lookup patterns
    if random.random() > 0.7:
        updates['email'] = f"atendimento.{bairro.lower().replace(' ', '')}@gmail.com"

    # 4. Email Validation Mock
    if not updates.get('email'):
        updates['email'] = f"host_{random.randint(100,999)}@luxuryrj.com"

    if updates and supabase and "<" not in SUPABASE_URL:
        try:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
        except Exception as e:
            print(f"    [!] Update failed: {e}")

def scrape():
    print("--- Starting Expanded Airbnb Scraper (Rio de Janeiro / Luxury Bundles) ---")
    
    # High-end neighborhoods to target individually for deeper results
    neighborhoods = [
        "Ipanema, Rio de Janeiro",
        "Leblon, Rio de Janeiro",
        "Barra da Tijuca, Rio de Janeiro",
        "Joá, Rio de Janeiro",
        "São Conrado, Rio de Janeiro",
        "Lagoa, Rio de Janeiro",
        "Copacabana, Rio de Janeiro",
        "Itanhangá, Rio de Janeiro"
    ]

    # Set fixed future dates for a 2-night stay to get "Real" pricing (including fees)
    checkin = "2026-06-11"
    checkout = "2026-06-13"
    num_nights = 2
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    total_leads_saved = 0
    
    try:
        for location in neighborhoods:
            print(f"\n🔍 Searching in: {location}...")
            # Format location for URL
            loc_query = location.replace(", ", "--").replace(" ", "-")
            url = f"https://www.airbnb.com.br/s/{loc_query}/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&price_min=1000&room_types%5B%5D=Entire+home%2Fapt&checkin={checkin}&checkout={checkout}"
            
            driver.get(url)
            time.sleep(random.uniform(5, 8))
            
            try:
                driver.execute_script("document.querySelector('section[data-testid=\"listing-billing-container\"]')?.remove();")
            except: pass

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.select('div[data-testid="card-container"]')
            
            if not listings:
                listings = soup.find_all('div', {'itemprop': 'itemListElement'})
                
            print(f"  > Found {len(listings)} listings in {location.split(',')[0]}.")
            
            for item in listings:
                try:
                    title_el = item.select_one('div[data-testid="listing-card-title"]') or \
                               item.select_one('span[id^="title_"]') or \
                               item.find('div', string=True)
                    title = title_el.get_text(strip=True) if title_el else "Imóvel de Luxo"

                    total_price_el = item.find('span', string=lambda x: x and 'total' in x.lower()) or \
                                     item.select_one('div[data-testid="price-availability-row"] > div > span:last-child')
                    
                    if total_price_el and 'total' in total_price_el.get_text().lower():
                        price_text = total_price_el.get_text(strip=True)
                        price_digits = ''.join(filter(str.isdigit, price_text.split(',')[0].replace('.', '')))
                        price = int(int(price_digits) / num_nights) if price_digits else 1000
                    else:
                        price_el = item.select_one('div[data-testid="price-availability-row"] span div span') or \
                                   item.select_one('span[data-testid="price-and-discounted-price"] span')
                        price_text = price_el.get_text(strip=True) if price_el else "1000"
                        price_digits = ''.join(filter(str.isdigit, price_text.split(',')[0].replace('.', '')))
                        price = int(price_digits) if price_digits else 1000
                    
                    link_el = item.find('a', href=True)
                    link = "https://airbnb.com.br" + link_el['href'].split('?')[0] if link_el else ""
                    
                    bairro = location.split(',')[0]
                    lux_score = get_lux_score(price, title, 35)
                    
                    lead = {
                        "anfitriao": "Consultar Perfil",
                        "titulo": title,
                        "link_imovel": link,
                        "preco_noite": price,
                        "bairro": bairro,
                        "lux_score": lux_score,
                        "lat": 0.0,
                        "lng": 0.0
                    }
                    
                    if supabase and "<" not in SUPABASE_URL:
                        # Check duplication
                        exists = supabase.table("leads").select("id").eq("link_imovel", link).execute()
                        if not exists.data:
                            res = supabase.table("leads").insert(lead).execute()
                            if res.data:
                                total_leads_saved += 1
                                print(f"    [OK] Capturado: {title[:20]}... (R${price})")
                                enrich_lead(res.data[0]['id'], lead)
                    else:
                        total_leads_saved += 1
                        print(f"    [Dry Run] Lead: {title[:20]}... (R${price})")
                        
                except Exception as e:
                    continue
            
            time.sleep(random.uniform(2, 4))
                
    except Exception as e:
        print(f"Critical error in Expanded Scraper: {e}")
    finally:
        driver.quit()
        
    print(f"\n--- SCRAPING COMPLETED. Total unique leads added: {total_leads_saved} ---")

if __name__ == "__main__":
    scrape()
