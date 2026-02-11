import os
import time
import random
import re
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
load_dotenv()

def get_env(key):
    return os.getenv(key) or os.getenv(key.upper())

SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_KEY = get_env("SUPABASE_KEY")
GOOGLE_API_KEY = get_env("GOOGLE_API")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL or SUPABASE_KEY missing in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Supabase OK.")

def get_desktop_driver():
    """Returns a Selenium Chrome driver configured as a desktop browser."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    try:
        svc = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=svc, options=opts)
    except:
        return webdriver.Chrome(options=opts)

# ──────────────────────────────────────────────
# LUXURY SCORE (Arithmetic – no AI)
# ──────────────────────────────────────────────
def get_lux_score(price, title, photos_count, badges=None):
    price_pts = min((price / 10000.0) * 50.0, 50.0)
    kws = ['luxo', 'luxury', 'vista mar', 'ocean view', 'cobertura',
           'penthouse', 'design', 'exclusivo']
    kw_pts = (sum(1 for k in kws if k in title.lower()) / len(kws)) * 30.0
    photo_pts = min((photos_count / 50.0) * 10.0, 10.0)
    badge_pts = 0
    if badges:
        if "Luxe" in badges: badge_pts = 10.0
        elif "Plus" in badges: badge_pts = 5.0
    return round(price_pts + kw_pts + photo_pts + badge_pts, 1)

# ──────────────────────────────────────────────
# PHASE 1 — DEEP SCRAPE (no AI, no quota)
# ──────────────────────────────────────────────
def deep_analyze_listing(driver, lead_id, url):
    """Scrapes a single listing for description, reviews, host info.
    NO AI calls — purely Selenium + BS4."""
    print(f"    [Scrape] {url[:60]}...")
    try:
        driver.get(url)
        time.sleep(random.uniform(5, 7))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text().lower()
        updates = {"intelligence_status": "scraped"}

        # ─── 1. Description ───
        desc_el = soup.select_one(
            'div[data-section-id="DESCRIPTION_DEFAULT"], '
            'div[data-testid="pdp-description-content"]')
        description = desc_el.get_text(strip=True) if desc_el else ""
        updates['descricao'] = description

        # ─── 2. Maintenance hooks ───
        maint_map = {
            'Mármore/Vidro': ['mármore', 'marble', 'vidro', 'glass', 'madeira maciça'],
            'Piscina/Jacuzzi': ['piscina', 'pool', 'jacuzzi', 'hidromassagem'],
            'Automação': ['automatizada', 'alexa', 'voice command', 'cinema', 'smart'],
            'Café Premium': ['nespresso', 'espresso', 'cafeteira']
        }
        found_maint = [lbl for lbl, kws in maint_map.items()
                       if any(k in page_text for k in kws)]
        updates['maintenance_items'] = found_maint

        # ─── 3. Cleanliness gap (reviews ≤ 4★) ───
        flags = ['poeira', 'sujo', 'limpeza', 'dust', 'dirty', 'mancha',
                 'odor', 'rodapé', 'suja', 'manchada']
        gap_mentions = []
        try:
            btn = driver.find_element(
                By.CSS_SELECTOR,
                'button[data-testid="pdp-show-all-reviews-button"]')
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except:
            pass

        for card in soup.select(
                'div[data-review-id], div[data-testid="pdp-review-card-content"]'):
            try:
                rating = 5
                r_el = card.select_one(
                    'span[aria-label*="estrela"], span[aria-label*="star"]')
                if r_el:
                    m = re.search(r'(\d)', r_el.get('aria-label', ''))
                    if m: rating = int(m.group(1))
                if rating <= 4:
                    t_el = card.select_one(
                        'span._163atp1, div[data-testid="pdp-review-description"]')
                    if t_el:
                        txt = t_el.get_text().lower()
                        if any(f in txt for f in flags):
                            gap_mentions.append(
                                f"({rating}★): {txt[:80].strip()}...")
            except:
                continue

        if gap_mentions:
            updates['cleanliness_gap'] = " | ".join(list(set(gap_mentions))[:3])
            print(f"      [!] {len(gap_mentions)} cleanliness reviews found.")

        # ─── 4. Host section (from listing page) ───
        # Fetch lead data first so we can update badges properly
        lead_row = supabase.table("leads").select(
            "titulo, preco_noite, bairro, anfitriao, badges"
        ).eq("id", lead_id).single().execute()
        lead_data = lead_row.data or {}

        host_section = soup.select_one(
            'div[data-testid="pdp-host-profile-section"]')
        other_listings = []

        if host_section:
            h_text = host_section.get_text()
            # Superhost badge
            is_superhost = "superhost" in h_text.lower()
            current_badges = lead_data.get('badges') or []
            if isinstance(current_badges, str):
                try: current_badges = json.loads(current_badges)
                except: current_badges = []
            if is_superhost and "Superhost" not in current_badges:
                current_badges.append("Superhost")
                updates['badges'] = current_badges

            # Host name extraction
            host_name_el = host_section.select_one('h2, h3')
            if host_name_el:
                raw_name = host_name_el.get_text(strip=True)
                # "Hospede-se com Maricy" → "Maricy"
                clean_name = re.sub(
                    r'(Hosted by|Hospede-se com)\s*', '', raw_name).strip()
                if clean_name:
                    updates['anfitriao'] = clean_name

        # ─── 5. Visit host profile for portfolio count ───
        # Search the ENTIRE page for the host link (not just host section)
        host_link = soup.select_one(
            'a[href*="/users/show/"], a[href*="/users/profile/"]')

        if host_link:
            href = host_link['href']
            host_url = href if href.startswith('http') else \
                "https://www.airbnb.com.br" + href
            print(f"      [Host] Visiting profile: {host_url}")
            try:
                driver.get(host_url)
                time.sleep(8)
                # Scroll down to load lazy elements
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(3)
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                prof_soup = BeautifulSoup(driver.page_source, 'html.parser')
                prof_text = prof_soup.get_text()

                # --- DEBUG: save a snippet of profile text for diagnostics ---
                print(f"      [Host] Profile text snippet (300 chars):")
                # Find text around "anúncio" or "listing" if present
                idx = prof_text.lower().find('anúncio')
                if idx == -1:
                    idx = prof_text.lower().find('listing')
                if idx == -1:
                    idx = prof_text.lower().find('acomodaç')
                if idx >= 0:
                    snippet = prof_text[max(0, idx-50):idx+100]
                    print(f"      >>> ...{snippet}...")
                else:
                    print(f"      >>> (no 'anúncio/listing' keyword found)")
                    print(f"      >>> First 300 chars: {prof_text[:300]}")

                # Portfolio count patterns
                patterns = [
                    r'[Vv]er\s+(?:os\s+)?(\d+)\s+an[uú]ncios',
                    r'[Ss]ee\s+all\s+(\d+)\s+listings',
                    r'(\d+)\s+acomoda[çc][õo]es',
                    r'(\d+)\s+places?\b',
                    r'[Ss]howing\s+(\d+)\s+listings',
                ]
                portfolio_size = 1
                for pat in patterns:
                    m = re.search(pat, prof_text)
                    if m:
                        portfolio_size = int(m.group(1))
                        break

                if portfolio_size > 1:
                    updates['host_portfolio_size'] = portfolio_size
                    print(f"      [Host] ✅ Portfolio: {portfolio_size} listings")
                else:
                    # Fallback: count visible cards
                    cards = prof_soup.select(
                        'div[data-testid="listing-card-title"], '
                        'div[data-testid="card-container"], '
                        'a[href*="/rooms/"]')
                    counted = len(set(c.get('href', c.text) for c in cards))
                    updates['host_portfolio_size'] = max(1, counted)
                    print(f"      [Host] Fallback count: "
                          f"{updates['host_portfolio_size']}")

                # Scrape visible listings
                seen = set()
                for a_tag in prof_soup.select('a[href*="/rooms/"]'):
                    room_href = a_tag['href'].split('?')[0]
                    room_url = ("https://www.airbnb.com.br" + room_href
                                if room_href.startswith('/') else room_href)
                    title_text = a_tag.get_text(strip=True)[:60] or "Listing"
                    if room_url not in seen:
                        other_listings.append(
                            {"title": title_text, "url": room_url})
                        seen.add(room_url)

                if other_listings:
                    print(f"      [Host] Scraped {len(other_listings)} "
                          f"property links.")

                driver.back()
                time.sleep(3)
            except Exception as he:
                print(f"      [!] Host profile error: {he}")
                try: driver.back()
                except: pass
        else:
            print("      [Host] No profile link found on page.")
            updates['host_portfolio_size'] = 1

        # ─── 6. Price verification ───
        try:
            price_el = soup.select_one(
                'span._1y74zjx, [data-testid="price-summary-total-price"]')
            if price_el:
                digits = ''.join(filter(str.isdigit,
                                        price_el.get_text().split(',')[0].replace('.', '')))
                if digits:
                    updates['preco_noite'] = int(int(digits) / 3)
                    print(f"      [Price] R$ {updates['preco_noite']}/night")
        except:
            pass

        # ─── 7. Store host listings in description ───
        if other_listings:
            host_block = f"--- HOST_LISTINGS_JSON ---\n{json.dumps(other_listings)}\n---"
            updates['descricao'] = f"{host_block}\n\n{description}"

        # ─── Save ───
        supabase.table("leads").update(updates).eq("id", lead_id).execute()
        print(f"      [DONE] Scrape complete for lead {lead_id}. "
              f"Status → 'scraped'")

    except Exception as e:
        print(f"    [!] Scrape Error: {e}")
        import traceback
        traceback.print_exc()
        supabase.table("leads").update(
            {"intelligence_status": "error"}
        ).eq("id", lead_id).execute()

# ──────────────────────────────────────────────
# PHASE 2 — AI ENRICHMENT (on already-scraped data)
# ──────────────────────────────────────────────
def enrich_with_ai():
    """Takes maintenance_items from scraped leads and generates a
    short sales pitch. Ultra-lightweight — no heavy classification."""
    try:
        from google import genai
        ai_client = genai.Client(api_key=GOOGLE_API_KEY)
        print("✅ Gemini connected.")
    except Exception as e:
        print(f"❌ Cannot initialize Gemini: {e}")
        return

    # Fetch scraped leads
    rows = supabase.table("leads").select(
        "id, titulo, maintenance_items, cleanliness_gap, anfitriao"
    ).eq("intelligence_status", "scraped").execute()

    if not rows.data:
        print("    No scraped leads awaiting AI.")
        return

    print(f"🧠 Generating pitches for {len(rows.data)} leads...")

    for lead in rows.data:
        lid = lead['id']
        title = lead.get('titulo', '') or ''
        maint = lead.get('maintenance_items') or []
        gap = lead.get('cleanliness_gap') or ''
        host = lead.get('anfitriao') or 'Proprietário'

        # Build context from what we scraped
        keywords = ', '.join(maint) if maint else 'Nenhum item especial'
        
        prompt = (
            f"Imóvel: {title}\n"
            f"Host: {host}\n"
            f"Itens de manutenção: {keywords}\n"
            f"Problemas de limpeza: {gap[:200] if gap else 'Nenhum'}\n\n"
            f"Crie uma frase de venda de 1 linha (máx 90 caracteres) "
            f"oferecendo serviço de limpeza/gestão profissional para este imóvel. "
            f"Foque nos itens de manutenção. Responda APENAS a frase, nada mais."
        )

        print(f"    [{lid[:8]}] '{title[:30]}' → maint: {keywords}")

        pitch = None
        for attempt in range(3):
            try:
                resp = ai_client.models.generate_content(
                    model='gemini-2.0-flash-lite',
                    contents=prompt
                )
                pitch = resp.text.strip()[:120]  # Cap length
                break
            except Exception as e:
                if "429" in str(e):
                    wait = 30 * (attempt + 1)
                    print(f"      [AI] Quota hit. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"      [!] Gemini error: {e}")
                break

        if pitch:
            upd = {
                "ai_report": pitch,
                "intelligence_status": "ready"
            }
            supabase.table("leads").update(upd).eq("id", lid).execute()
            print(f"      ✅ Pitch: \"{pitch}\"")
        else:
            print(f"      ⚠️ No pitch generated for {lid[:8]}.")

        time.sleep(1)  # Be gentle

    print("🧠 AI enrichment complete.")

# ──────────────────────────────────────────────
# SEARCH — Fast scrape search results
# ──────────────────────────────────────────────
def scrape_main_leads():
    """Fast scrape to populate the database with new opportunities."""
    print("--- Running Main Scraper (Fast Phase) ---")
    neighborhoods = [
        "Ipanema", "Leblon", "Barra da Tijuca", "Joá", "São Conrado",
        "Lagoa", "Copacabana", "Itanhangá", "Guaratiba", "Botafogo",
        "Vargem Grande", "Vargem Pequena", "Ilha de Guaratiba"
    ]
    checkin_dt = datetime.now() + timedelta(days=14)
    checkout_dt = checkin_dt + timedelta(days=3)
    checkin = checkin_dt.strftime("%Y-%m-%d")
    checkout = checkout_dt.strftime("%Y-%m-%d")
    num_nights = 3

    driver = get_desktop_driver()
    try:
        for loc in neighborhoods:
            print(f" 🔍 Neighborhood: {loc}")
            url = (f"https://www.airbnb.com.br/s/{loc}--Rio-de-Janeiro--RJ/"
                   f"homes?price_min=1000&room_types%5B%5D=Entire+home%2Fapt"
                   f"&checkin={checkin}&checkout={checkout}")
            driver.get(url)
            time.sleep(5)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.select('div[data-testid="card-container"]')

            for item in listings[:20]:
                try:
                    title_el = item.select_one(
                        'div[data-testid="listing-card-title"]')
                    title = (title_el.get_text(strip=True)
                             if title_el else "Luxury Property")

                    price_el = item.select_one(
                        'div[data-testid="price-availability-row"] div')
                    price = 1000
                    if price_el:
                        ptxt = price_el.get_text()
                        nm = re.search(r'por (\d+) noit', ptxt)
                        denom = int(nm.group(1)) if nm else 1
                        digits = ''.join(filter(
                            str.isdigit,
                            ptxt.split(',')[0].replace('.', '')))
                        if digits:
                            val = int(digits)
                            price = (int(val / (denom if denom > 1
                                                 else num_nights))
                                     if denom > 1 or val > 5000 else val)

                    link_el = item.find('a', href=True)
                    link = ("https://airbnb.com.br"
                            + link_el['href'].split('?')[0]
                            if link_el else "")

                    if link:
                        exists = supabase.table("leads").select("id").eq(
                            "link_imovel", link).execute()
                        if not exists.data:
                            lead = {
                                "titulo": title,
                                "link_imovel": link,
                                "preco_noite": price,
                                "bairro": loc,
                                "lux_score": get_lux_score(price, title, 30),
                                "intelligence_status": "pending"
                            }
                            supabase.table("leads").insert(lead).execute()
                            print(f"    [+] {title[:25]}...")
                except:
                    continue
    finally:
        driver.quit()

# ──────────────────────────────────────────────
# WATCHER — Waits for app requests
# ──────────────────────────────────────────────
def start_watcher():
    """Stays active and waits for 'pending' requests from the app."""
    print("\n🚀 [WATCHER] Scrape Engine is ACTIVE.")
    print("Requests from your phone will be processed here.\n")

    while True:
        try:
            pending = supabase.table("leads").select(
                "id, link_imovel"
            ).eq("intelligence_status", "pending").execute()

            if pending.data:
                print(f"🔔 {len(pending.data)} lead(s) to scrape...")
                driver = get_desktop_driver()
                try:
                    for p in pending.data:
                        deep_analyze_listing(
                            driver, p['id'], p['link_imovel'])
                finally:
                    driver.quit()
                    print("✅ Scrape batch done. Waiting...\n")
        except Exception as e:
            print(f"Watcher error: {e}")

        time.sleep(5)

# ──────────────────────────────────────────────
# PROCESS PENDING (one-off)
# ──────────────────────────────────────────────
def process_pending_once():
    """Finds all pending leads and scrapes them once."""
    pending = supabase.table("leads").select(
        "id, link_imovel"
    ).eq("intelligence_status", "pending").execute()

    if not pending.data:
        print("    No pending leads.")
        return

    print(f"🔔 {len(pending.data)} leads to scrape...")
    driver = get_desktop_driver()
    try:
        for p in pending.data:
            deep_analyze_listing(driver, p['id'], p['link_imovel'])
    finally:
        driver.quit()

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    mode = "watcher"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    print(f"--- ZAI INTELLIGENCE ENGINE: {mode.upper()} ---")

    # ── Single URL mode ──
    if mode.startswith("http"):
        url = mode.split('?')[0]
        print(f"🎯 Targeted scrape: {url}")
        driver = get_desktop_driver()
        try:
            exists = supabase.table("leads").select("id").eq(
                "link_imovel", url).execute()
            if exists.data:
                lid = exists.data[0]['id']
            else:
                res = supabase.table("leads").insert({
                    "titulo": "Manual Target",
                    "link_imovel": url,
                    "intelligence_status": "pending",
                    "bairro": "Manual"
                }).execute()
                lid = res.data[0]['id']
            deep_analyze_listing(driver, lid, url)
        finally:
            driver.quit()
        sys.exit(0)

    # ── Named modes ──
    mode = mode.lower()

    if "search" in mode:
        scrape_main_leads()
        print("\n⚡ Now scraping all pending leads...")
        process_pending_once()

    elif "deep" in mode:
        process_pending_once()

    elif "ai" in mode:
        # NEW: AI-only mode — enrich already-scraped leads
        enrich_with_ai()

    elif "watcher" in mode:
        start_watcher()

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: scraper.py [watcher|search|deep|ai|<URL>]")
