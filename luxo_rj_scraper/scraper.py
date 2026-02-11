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
from google import genai
from datetime import datetime, timedelta
import json

def get_driver_options():
    """Returns optimized Chrome options to force DESKTOP behavior."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    # Professional Desktop User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return options
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

# Initialize Gemini Client
ai_client = None
if GOOGLE_API_KEY:
    try:
        ai_client = genai.Client(api_key=GOOGLE_API_KEY)
        print("✅ Gemini AI (New SDK) initialized.")
    except Exception as e:
        print(f"⚠️ Warning: Gemini initialization failed: {e}")
else:
    print("⚠️ Warning: GOOGLE_API key missing. AI intelligence will be skipped.")

def get_ai_intelligence(description, title, price, photos, reviews, bairro, anfitriao):
    """Unified AI Intelligence: Returns JSON with Lux Score, Combat Report, and WA Hook."""
    if not ai_client:
        return None
    
    prompt = f"""
    Você é um classificador de imóveis de luxo e mestre em vendas. 
    Analise o imóvel abaixo e responda estritamente no formato JSON:
    {{
      "luxury": float (0.0 a 1.0),
      "reason": "por que ele tem esse score?",
      "combat_report": {{ "dor": "...", "gancho": "..." }},
      "wa_hook": "Frase de 90 chars p/ WhatsApp vendendo limpeza/gestão baseada nos problemas detectados."
    }}

    DADOS:
    - Título: {title}
    - Preço: R$ {price}/noite
    - Fotos: {photos}
    - Bairro: {bairro}
    - Host: {anfitriao}
    - Descrição: {description[:1000]}
    - Reviews: {reviews[:1000]}
    """

    for attempt in range(3):
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                print(f"      [AI] Quota hit (429). Waiting 60s for reset...")
                time.sleep(60)
                continue
            print(f"      [!] Gemini Error: {e}")
            break
    return None

def get_lux_score(price, title, photos_count, badges=None):
    # 1. Price Component (Max 50 pts) - Linear scale up to R$ 10.000
    price_points = min((price / 10000.0) * 50.0, 50.0)
    
    # 2. Keywords Component (Max 30 pts)
    keywords = ['luxo', 'luxury', 'vista mar', 'ocean view', 'cobertura', 'penthouse', 'design', 'exclusivo']
    lower_title = title.lower()
    found_count = sum(1 for kw in keywords if kw in lower_title)
    kw_points = (found_count / len(keywords)) * 30.0
    
    # 3. Features & Badges (Max 20 pts)
    photo_points = min((photos_count / 50.0) * 10.0, 10.0)
    badge_points = 0
    if badges:
        if "Luxe" in badges: badge_points = 10.0
        elif "Plus" in badges: badge_points = 5.0
        
    return round(price_points + kw_points + photo_points + badge_points, 1)

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
        host_section = soup.select_one('div[data-testid="pdp-host-profile-section"]')
        other_listings = []
        if host_section:
            txt = host_section.get_text()
            # Superhost check
            is_superhost = "superhost" in txt.lower()
            if 'badges' not in l: l['badges'] = []
            if is_superhost and "Superhost" not in l['badges']:
                l['badges'].append("Superhost")
                updates['badges'] = l['badges']
            
            # 4. Host Profile Discovery & Portfolio Scraping
            # Be more aggressive finding the link (sometimes it's an overlay or image link)
            host_link_el = soup.select_one('a[href*="/users/show/"], a[href*="/users/profile/"]')
            
            # Fallback: Try to find Host ID in text if no link
            host_id = None
            if not host_link_el:
                id_match = re.search(r'/users/(\d+)', driver.current_url)
                if id_match: host_id = id_match.group(1)
            
            if host_link_el or host_id:
                h_href = host_link_el['href'] if host_link_el else f"/users/show/{host_id}"
                host_url = h_href if h_href.startswith('http') else "https://www.airbnb.com.br" + h_href
                
                print(f"      [Host] Target Profile: {host_url}")
                try:
                    driver.get(host_url)
                    time.sleep(8) # Robust wait for profile depth
                    
                    # Scroll to ensure all dynamic blocks (like "See all listings") load
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(3)
                    
                    host_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    profile_text = host_soup.get_text()
                    
                    # A) Accurate Portfolio Count (Fator de Escala)
                    # Use a more explicit regex to avoid matching "reviews" or "years"
                    # We look for "Ver os X anúncios" or "Showing X places"
                    patterns = [
                        r'[Vv]er os\s+(\d+)\s+anúncios',
                        r'[Ss]ee all\s+(\d+)\s+listings',
                        r'(\d+)\s+acomodações',
                        r'(\d+)\s+places'
                    ]
                    
                    found_size = 1
                    for p in patterns:
                        m = re.search(p, profile_text)
                        if m:
                            found_size = int(m.group(1))
                            break
                    
                    if found_size > 1:
                        updates['host_portfolio_size'] = found_size
                        print(f"      [Host] SUCCESS: Identified {found_size} listings.")
                    else:
                        # Fallback: Count visible cards on profile
                        visible_cards = host_soup.select('div[data-testid="listing-card-title"], div[data-testid="card-container"]')
                        updates['host_portfolio_size'] = max(1, len(visible_cards))
                        print(f"      [Host] Fallback: Counted {updates['host_portfolio_size']} visible cards.")
                    
                    # B) Scrape the reference properties
                    cards = host_soup.select('div[data-testid="listing-card-title"], div[data-testid="card-container"]')
                    
                    # B) Scrape the properties
                    # If there's a "See all" link, we could follow it, but for now we take the visible ones
                    cards = host_soup.select('div[data-testid="listing-card-title"], div[data-testid="card-container"]')
                    seen_links = set()
                    for card in cards:
                        link_el = card.select_one('a[href*="/rooms/"]') or card.find_parent('a', href=True)
                        if link_el:
                            l_url = "https://airbnb.com.br" + link_el['href'].split('?')[0]
                            # Extract clean title
                            l_title = card.get_text(strip=True).replace('Novo listing', '').strip()
                            if l_url not in seen_links and "/rooms/" in l_url:
                                other_listings.append({"title": l_title, "url": l_url})
                                seen_links.add(l_url)
                    
                    print(f"      [Host] Cataloged {len(other_listings)} reference properties.")
                    driver.back()
                    time.sleep(3)
                except Exception as he:
                    print(f"      [!] Profile Scraping Depth Error: {he}")
                    try: driver.back()
                    except: pass
        
        # 4.5 Precise Price Verification (Booking Widget)
        try:
            booking_price_el = soup.select_one('span._1y74zjx, [data-testid="price-summary-total-price"]')
            if booking_price_el:
                p_text = booking_price_el.get_text()
                p_digits = ''.join(filter(str.isdigit, p_text.split(',')[0].replace('.', '')))
                if p_digits:
                    raw_p = int(p_digits)
                    # Use a 3-night fallback as set in the main scraper
                    updates['preco_noite'] = int(raw_p / 3)
                    print(f"      [Price] Verified: R$ {updates['preco_noite']}/night")
        except: pass

        # 5. AI Sales Intelligence (Gemini 2.0 Unified)
        print("      [AI] Generating Unified Intelligence & Hooks...")
        all_reviews_text = " | ".join(gap_mentions)
        
        # Get host name and neighborhood from the lead row if possible
        lead_data = supabase.table("leads").select("titulo, preco_noite, bairro, anfitriao, badges").eq("id", lead_id).single().execute()
        l = lead_data.data or {}
        
        ai_json = get_ai_intelligence(
            description, 
            l.get('titulo', ''), 
            l.get('preco_noite', 0), 
            len(soup.select('img')), # Quick photo count
            all_reviews_text,
            l.get('bairro', ''),
            l.get('anfitriao', 'Proprietário')
        )
        
        if ai_json:
            updates['ai_report'] = ai_json # Now storing JSON
            
            # Clean up old tags in description if they exist
            import re
            clean_desc = re.sub(r'--- (AI_INTEL|HOST_LISTINGS)_JSON ---.*?---', '', description, flags=re.DOTALL).strip()
            
            # Fallback: Tag description for easy parsing
            desc_intel = f"--- AI_INTEL_JSON ---\n{ai_json}\n---"
            host_intel = ""
            if other_listings:
                host_intel = f"--- HOST_LISTINGS_JSON ---\n{json.dumps(other_listings)}\n---"
            
            updates['descricao'] = f"{desc_intel}\n{host_intel}\n\n{clean_desc}"
            
            # Extract score if possible to update lux_score column
            try:
                import json
                parsed = json.loads(ai_json)
                updates['lux_score'] = int(parsed.get('luxury', 0.5) * 100)
            except: pass

        if supabase:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
        print(f"      [DONE] Strategic Intelligence generated for lead {lead_id}.")
        
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
    # Dynamic Date Calculation: 2 weeks from today, 3 nights stay
    checkin_dt = datetime.now() + timedelta(days=14)
    checkout_dt = checkin_dt + timedelta(days=3)
    
    checkin = checkin_dt.strftime("%Y-%m-%d")
    checkout = checkout_dt.strftime("%Y-%m-%d")
    num_nights = 3
    
    options = get_driver_options()
    
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
                    
                    price_el = item.select_one('div[data-testid="price-availability-row"] div, [data-testid="price-summary-total-price"]')
                    price = 1000
                    if price_el:
                        price_text = price_el.get_text()
                        # Detect total price vs nightly price
                        nights_match = re.search(r'por (\d+) noit', price_text)
                        denom = int(nights_match.group(1)) if nights_match else 1
                        
                        digits = ''.join(filter(str.isdigit, price_text.split(',')[0].replace('.', '')))
                        if digits:
                            found_val = int(digits)
                            # If it's a total, divide. If it's already low, it might be nightly.
                            if denom > 1 or found_val > 5000:
                                price = int(found_val / (denom if denom > 1 else num_nights))
                            else:
                                price = found_val

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
                options = get_driver_options()
                
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
        
        options = get_driver_options()
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
