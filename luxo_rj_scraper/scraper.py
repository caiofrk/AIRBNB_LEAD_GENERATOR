import os
import time
import random
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    # Price based score
    if price >= 1000: score += 15
    if price >= 3000: score += 15
    if price >= 5000: score += 10
    
    # Keywords
    keywords = ['luxo', 'luxury', 'vista mar', 'ocean view', 'cobertura', 'penthouse', 'design', 'exclusivo']
    lower_title = title.lower()
    for kw in keywords:
        if kw in lower_title:
            score += 5
            
    # Badges
    if badges:
        if "Luxe" in badges: score += 30
        if "Plus" in badges: score += 15
        if "Favorito" in badges: score += 10
    
    return min(score, 100)

def deep_enrich_lead(driver, lead_id, url):
    """Visits the individual listing page to extract deep sales intelligence."""
    print(f"    [Deep Scrape] Visiting listing: {url[:50]}...")
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(url)
        time.sleep(random.uniform(4, 6))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        updates = {}

        # 1. Listing Category / Badges
        badges = []
        badge_els = soup.select('div[data-testid="listing-card-badge"], span[class*="luxe"], div[class*="plus"]')
        for b in badge_els:
            txt = b.get_text(strip=True)
            if txt: badges.append(txt)
        
        # Look for specific text badges
        page_text = soup.get_text()
        if "Luxe" in page_text: badges.append("Luxe")
        if "Plus" in page_text: badges.append("Plus")
        if "Favorito dos hóspedes" in page_text: badges.append("Guest Favorite")
        updates['badges'] = list(set(badges))

        # 2. Amenity-Specific Maintenance
        maintenance_keywords = {
            'hot_tub': ['hidromassagem', 'jacuzzi', 'banheira', 'hot tub'],
            'sauna': ['sauna'],
            'espresso': ['nespresso', 'espresso', 'cafeteira'],
            'surfaces': ['mármore', 'marble', 'vidro', 'glass', 'madeira maciça', 'solid wood'],
            'luxury_appliances': ['viking', 'sub-zero', 'wolf', 'miele', 'smeg']
        }
        found_maintenance = []
        for category, kws in maintenance_keywords.items():
            for kw in kws:
                if kw in page_text.lower():
                    found_maintenance.append(category)
                    break
        updates['maintenance_items'] = list(set(found_maintenance))

        # 3. Cleanliness Gap (Review Sentiment Analysis)
        cleanliness_red_flags = ['poeira', 'sujo', 'limpeza', 'dust', 'dirty', 'cleaning', 'mancha', 'cheiro', 'odor', 'baseboard', 'rodapé', 'glassware', 'taça', 'fingerprint', 'digital', "manchado", "manchada", "manchados", "manchadas"]
        gap_mentions = []
        
        # Get reviews (usually in sections or modal)
        review_texts = [r.get_text().lower() for r in soup.select('span.ll4r2nl, div[data-testid="pdp-reviews-modal-scrollable-container"] span')]
        for text in review_texts:
            for flag in cleanliness_red_flags:
                if flag in text:
                    # Capture a snippet
                    snippet = text[max(0, text.find(flag)-30) : min(len(text), text.find(flag)+50)]
                    gap_mentions.append(snippet.strip())
                    break
        
        if gap_mentions:
            updates['cleanliness_gap'] = " | ".join(list(set(gap_mentions))[:3])
            print(f"      [!] Cleanliness Gap Found: {updates['cleanliness_gap'][:50]}...")

        # 4. Occupancy & Turnover Stress
        # Heuristic: Count reviews in the last 30 days
        # This is a bit complex without dates, so we'll look for "Recent" keywords or high review count
        review_count_el = soup.select_one('button[data-testid="pdp-show-all-reviews-button"]')
        if review_count_el:
            count_match = re.search(r'(\d+)', review_count_el.get_text())
            if count_match:
                total_reviews = int(count_match.group(1))
                if total_reviews > 50:
                    updates['turnover_stress'] = "Alta Rotatividade (>50 reviews)"
                elif total_reviews < 5:
                    updates['turnover_stress'] = "Baixa Ocupação / Novo"

        # 5. Host Portfolio Size
        host_section = soup.select_one('div[data-testid="pdp-host-profile-section"]')
        if host_section:
            host_text = host_section.get_text().lower()
            portfolio_match = re.search(r'(\d+)\s+anúncios', host_text)
            if portfolio_match:
                updates['host_portfolio_size'] = int(portfolio_match.group(1))
            else:
                updates['host_portfolio_size'] = 1 # Assume individual if not specified

        if updates and supabase:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
            print(f"      [OK] Deep Intelligence Updated.")

    except Exception as e:
        print(f"    [!] Error in Deep Scrape: {e}")
    finally:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

def scrape():
    print("--- Starting Advanced Intelligence Scraper (Rio Luxury Tier) ---")
    
    neighborhoods = [
        "Ipanema, Rio de Janeiro", "Leblon, Rio de Janeiro", "Barra da Tijuca, Rio de Janeiro",
        "Joá, Rio de Janeiro", "São Conrado, Rio de Janeiro", "Lagoa, Rio de Janeiro",
        "Copacabana, Rio de Janeiro", "Itanhangá, Rio de Janeiro", "Guaratiba, Rio de Janeiro",
        "Botafogo, Rio de Janeiro", "Vargem Grande, Rio de Janeiro", "Vargem Pequena, Rio de Janeiro",
        "Ilha de Guaratiba, Rio de Janeiro"
    ]

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
            print(f"\n🔍 Neighborhood: {location}")
            loc_query = location.replace(", ", "--").replace(" ", "-")
            url = f"https://www.airbnb.com.br/s/{loc_query}/homes?price_min=1000&room_types%5B%5D=Entire+home%2Fapt&checkin={checkin}&checkout={checkout}"
            
            driver.get(url)
            time.sleep(random.uniform(6, 9))
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.select('div[data-testid="card-container"]')
            
            for item in listings[:15]: # Limit per neighborhood for efficiency
                try:
                    title_el = item.select_one('div[data-testid="listing-card-title"]')
                    title = title_el.get_text(strip=True) if title_el else "Imóvel de Luxo"

                    total_price_el = item.select_one('div[data-testid="price-availability-row"] > div > span:last-child')
                    price = 1000
                    if total_price_el:
                        price_text = total_price_el.get_text(strip=True)
                        price_digits = ''.join(filter(str.isdigit, price_text.split(',')[0].replace('.', '')))
                        price = int(int(price_digits) / num_nights) if price_digits else 1000
                    
                    link_el = item.find('a', href=True)
                    if not link_el: continue
                    link = "https://airbnb.com.br" + link_el['href'].split('?')[0]
                    
                    bairro = location.split(',')[0]
                    
                    if supabase:
                        exists = supabase.table("leads").select("id").eq("link_imovel", link).execute()
                        if not exists.data:
                            lux_score = get_lux_score(price, title, 35)
                            lead_data = {
                                "titulo": title, "link_imovel": link, "preco_noite": price,
                                "bairro": bairro, "lux_score": lux_score, "contatado": False
                            }
                            res = supabase.table("leads").insert(lead_data).execute()
                            if res.data:
                                lead_id = res.data[0]['id']
                                total_leads_saved += 1
                                # Deep Enrichment
                                deep_enrich_lead(driver, lead_id, link)
                                time.sleep(random.uniform(2, 4))
                except Exception as e:
                    print(f"      [!] Error processing card: {e}")
                    continue
            
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        driver.quit()
        
    print(f"\n--- SUCCESS. {total_leads_saved} High-Intelligence Leads Processed ---")

if __name__ == "__main__":
    scrape()
