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

def get_env_or_secret(key):
    val = os.getenv(key)
    if not val:
        # Check for capitalized version (standard in secrets)
        val = os.getenv(key.upper())
    return val

SUPABASE_URL = get_env_or_secret("SUPABASE_URL")
SUPABASE_KEY = get_env_or_secret("SUPABASE_KEY")
GOOGLE_API_KEY = get_env_or_secret("GOOGLE_API")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: SUPABASE_URL or SUPABASE_KEY is missing!")
    print("Please ensure these are set in your .env file (local) or GitHub Secrets (cloud).")
    exit(1)

# Initialize Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connection initialized.")
except Exception as e:
    print(f"❌ ERROR: Supabase connection failed: {e}")
    exit(1)

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

        # 3. Cleanliness Gap (Focused on reviews <= 4 stars)
        flags = ['poeira', 'sujo', 'limpeza', 'dust', 'dirty', 'mancha', 'odor', 'baseboard', 'rodapé', 'fingerprint', 'suja', 'manchada']
        gap_mentions = []

        # Try to open the reviews modal to get more data (including those rare <= 4 star reviews)
        try:
            show_all_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="pdp-show-all-reviews-button"]')
            driver.execute_script("arguments[0].click();", show_all_btn)
            time.sleep(3)
            # Update soup with modal content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except:
            pass # Fallback to what's visible on the page

        # Find individual review elements
        # Airbnb usually groups reviews in cards
        review_cards = soup.select('div[data-review-id], div[data-testid="pdp-review-card-content"]')
        
        for card in review_cards:
            try:
                # Find rating: Airbnb uses aria-label like "Avaliado com 4 de 5 estrelas"
                rating = 5 # Default to 5
                rating_el = card.select_one('span[aria-label*="estrela"], span[aria-label*="star"]')
                if rating_el:
                    label = rating_el.get('aria-label', '').lower()
                    # Extract the first digit (the rating)
                    match = re.search(r'(\d)', label)
                    if match:
                        rating = int(match.group(1))

                # User requirement: Ignore 5-star reviews
                if rating <= 4:
                    # Get the text of this specific review
                    review_text_el = card.select_one('span._163atp1, div[data-testid="pdp-review-description"]')
                    if review_text_el:
                        txt = review_text_el.get_text().lower()
                        if any(f in txt for f in flags):
                            # Prepend rating to show context in the app
                            gap_mentions.append(f"({rating}*): {txt[:80].strip()}...")
            except:
                continue
        
        if gap_mentions:
            updates['cleanliness_gap'] = " | ".join(list(set(gap_mentions))[:3])
            print(f"      [!] Found {len(gap_mentions)} critical reviews.")

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
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ Local Chrome failure: {e}. Trying simple initialization...")
        driver = webdriver.Chrome(options=options)

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
                            # All new leads are now created as 'pending' by default 
                            # to trigger immediate deep analysis.
                            lead = {
                                "titulo": title, 
                                "link_imovel": link, 
                                "preco_noite": price, 
                                "bairro": loc, 
                                "lux_score": get_lux_score(price, title, 30),
                                "intelligence_status": "pending" 
                            }
                            supabase.table("leads").insert(lead).execute()
                            print(f"    [+] New Opportunity Found: {title[:20]} (Marked for analysis)")
                        else:
                            # If lead exists but has NO intelligence, mark it as pending
                            current = exists.data[0]
                            # Using .get for safety if column is missing locally
                            if current.get('intelligence_status') == 'none' or current.get('intelligence_status') is None:
                                supabase.table("leads").update({"intelligence_status": "pending"}).eq("id", current['id']).execute()
                                print(f"    [*] Existing lead {title[:15]} sent back for analysis.")
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
    
    # Check execution mode
    mode = "watcher"
    if len(sys.argv) > 1:
        mode = sys.argv[1] # Keep case for URLs
    
    print(f"--- AIRBNB INTELLIGENCE ENGINE: {mode.upper()} ---")
    
    # NEW: Single Property/URL Mode
    if mode.startswith("http"):
        url = mode.split('?')[0] # Clean URL
        print(f"🎯 Targeted Analysis: {url}")
        
        options = Options()
        options.add_argument("--headless=new")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        try:
            # Check if lead exists, if not, create a placeholder
            exists = supabase.table("leads").select("id").eq("link_imovel", url).execute()
            if exists.data:
                lead_id = exists.data[0]['id']
            else:
                print("      [+] Creating new lead entry for this URL...")
                new_lead = {
                    "titulo": "Manual Target",
                    "link_imovel": url,
                    "intelligence_status": "pending",
                    "bairro": "Manual"
                }
                res = supabase.table("leads").insert(new_lead).execute()
                lead_id = res.data[0]['id']
            
            deep_analyze_listing(driver, lead_id, url)
            print(f"✅ Analysis complete for manual target.")
        finally:
            driver.quit()
        sys.exit(0)

    # Standard Modes
    mode = mode.lower()
    if "search" in mode:
        # Step 1: Find new leads (they will be marked as 'pending')
        scrape_main_leads()
        
        # Step 2: Immediately process all pending intelligence found in Step 1
        # This makes 'Intelligence' the default for all new leads.
        print("\n⚡ Starting immediate enrichment for discovered leads...")
        process_pending_once() 
    
    if "deep" in mode:
        print("--- Running Deep Intelligence (Single Run) ---")
        process_pending_once()
    elif "watcher" in mode:
        # Step 3: Local Watcher mode (stays alive for on-demand app requests)
        start_watcher()
    else:
        print(f"Done with tasks (Mode: {mode}).")

def process_pending_once():
    """Finds all pending leads and runs deep analysis once. Used by Cloud and Search modes."""
    try:
        pending = supabase.table("leads").select("id, link_imovel").eq("intelligence_status", "pending").execute()
        if pending.data:
            print(f"🔔 Found {len(pending.data)} leads awaiting analysis. Processing...")
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except:
                driver = webdriver.Chrome(options=options)
                
            try:
                for p in pending.data:
                    deep_analyze_listing(driver, p['id'], p['link_imovel'])
            finally:
                driver.quit()
        else:
            print("    No pending analysis found.")
    except Exception as e:
        print(f"❌ Analysis error: {e}")
