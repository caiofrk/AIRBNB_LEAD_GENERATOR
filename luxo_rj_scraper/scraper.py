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

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL or SUPABASE_KEY missing in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Supabase OK.")

def get_desktop_driver():
    """Returns a Chrome driver configured as a full desktop browser."""
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
# LUXURY SCORE (Arithmetic — no AI)
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
# DEEP SCRAPE — visits a listing, gets everything
# ──────────────────────────────────────────────
def deep_analyze_listing(driver, lead_id, url):
    """Scrapes a single listing: description, reviews, host profile, portfolio.
    NO AI. Purely Selenium + BS4. Status → 'ready' when done."""
    print(f"\n    ╔══ [Scrape] {url[:60]}...")
    try:
        driver.get(url)
        time.sleep(random.uniform(5, 7))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text().lower()
        updates = {"intelligence_status": "ready"}

        # ─── 1. Description ───
        desc_el = soup.select_one(
            'div[data-section-id="DESCRIPTION_DEFAULT"], '
            'div[data-testid="pdp-description-content"]')
        description = desc_el.get_text(strip=True) if desc_el else ""
        updates['descricao'] = description
        print(f"    ║ Description: {len(description)} chars")

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
        print(f"    ║ Maintenance: {found_maint}")

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
            print(f"    ║ Cleanliness gaps: {len(gap_mentions)}")

        # ─── 4. Host section — badges + name ───
        lead_row = supabase.table("leads").select(
            "titulo, preco_noite, bairro, anfitriao, badges"
        ).eq("id", lead_id).single().execute()
        lead_data = lead_row.data or {}

        # Try multiple selectors for host section
        host_selectors = [
            'div[data-section-id="HOST_PROFILE_DEFAULT"]',
            'div[data-testid="pdp-host-profile-section"]',
            'div[data-section-id="HOST_OVERVIEW_DEFAULT"]',
            'section[data-section-id="HOST_PROFILE_DEFAULT"]',
        ]
        host_section = None
        for sel in host_selectors:
            host_section = soup.select_one(sel)
            if host_section:
                print(f"    ║ Host section via: {sel}")
                break

        # Fallback: find by text content (anfitrião/anfitriã/superhost)
        if not host_section:
            for section in soup.select('section, div[data-section-id]'):
                txt = section.get_text().lower()
                if any(kw in txt for kw in [
                    'anfitrião', 'anfitriã', 'hosted by',
                    'superhost', 'superanfitrião'
                ]):
                    host_section = section
                    sid = section.get('data-section-id', '?')
                    print(f"    ║ Host section via TEXT MATCH "
                          f"(tag={section.name}, section-id={sid})")
                    break

        if not host_section:
            # Dump page structure for debugging
            testids = [el.get('data-testid') for el in
                       soup.select('[data-testid]')][:20]
            section_ids = [el.get('data-section-id') for el in
                           soup.select('[data-section-id]')][:20]
            print(f"    ║ ⚠ HOST SECTION NOT FOUND!")
            print(f"    ║ data-testid on page: {testids}")
            print(f"    ║ data-section-id on page: {section_ids}")
            full_text = soup.get_text()
            for kw in ['anfitrião', 'anfitriã', 'hosted by', 'superhost']:
                idx = full_text.lower().find(kw)
                if idx >= 0:
                    snip = full_text[max(0, idx-30):idx+80].strip()
                    print(f"    ║ '{kw}' in page text: «{snip}»")

        print(f"    ║ Host section found: {host_section is not None}")


        if host_section:
            h_text = host_section.get_text()
            print(f"    ║ Host section text (200ch): {h_text[:200]}")

            # Superhost badge (EN + PT)
            is_superhost = any(kw in h_text.lower() for kw in [
                'superhost', 'superanfitrião', 'superanfitriã'])
            print(f"    ║ Superhost: {is_superhost}")
            current_badges = lead_data.get('badges') or []
            if isinstance(current_badges, str):
                try: current_badges = json.loads(current_badges)
                except: current_badges = []
            if is_superhost and "Superhost" not in current_badges:
                current_badges.append("Superhost")
                updates['badges'] = current_badges

            # Host name — extract from section text, NOT from h2/h3
            # (h2/h3 often picks up "Consultar Perfil" button text)
            host_name = None

            # Try regex patterns on the section text
            name_patterns = [
                r'Anfitri[ãa]\(?o?\)?[:\s]+([A-ZÀ-Ú][\w\s\-&\.]+)',
                r'Hosted by\s+(.+?)(?:\s*$|\s*Superhost)',
                r'Hospede-se com\s+(.+?)(?:\s*$|\s*Superhost)',
            ]
            for pat in name_patterns:
                m = re.search(pat, h_text)
                if m:
                    candidate = m.group(1).strip()
                    # Filter out garbage
                    if candidate and candidate.lower() not in [
                        'consultar perfil', 'ver perfil', 'profile'
                    ]:
                        host_name = candidate
                        break

            # Fallback: try h2/h3 but filter garbage
            if not host_name:
                host_name_el = host_section.select_one('h2, h3, h1')
                if host_name_el:
                    raw = host_name_el.get_text(strip=True)
                    raw = re.sub(
                        r'(Hosted by|Hospede-se com|Anfitriã?o:?\s*)',
                        '', raw, flags=re.IGNORECASE).strip()
                    if raw and raw.lower() not in [
                        'consultar perfil', 'ver perfil', 'profile'
                    ]:
                        host_name = raw

            # Clean trailing garbage from host name
            if host_name:
                # Strip "Superhost" suffix (often stuck to name)
                host_name = re.sub(r'Superhost.*$', '', host_name,
                                   flags=re.IGNORECASE).strip()
                # Strip "X anos hospedando" suffix
                host_name = re.sub(r'\d+\s*anos?\s*hospedando.*$', '',
                                   host_name, flags=re.IGNORECASE).strip()
                # Strip trailing dots/spaces/special chars
                host_name = host_name.rstrip(' ·.·')

            if host_name:
                updates['anfitriao'] = host_name
                print(f"    ║ Host name: {host_name}")
            else:
                print(f"    ║ ⚠ Could not extract host name")

        # ─── 5. HOST PROFILE — find the HOST (not a commenter!) ───
        # KEY: Airbnb marks host links with ?previous_page_name=PdpHomeMarketplace
        # KEY: /users/show/ REDIRECTS to login! Use /users/profile/ instead!
        navigated_to_profile = False

        # Strategy 1: Search raw HTML for host profile URL with Pdp marker
        raw_html = driver.page_source
        host_url_match = re.search(
            r'/users/(?:show|profile)/(\d+)\?[^"\']*PdpHomeMarketplace',
            raw_html)

        host_id = None
        if host_url_match:
            host_id = host_url_match.group(1)
            print(f"    ║ ✅ HOST ID found via PdpMarker: {host_id}")
        else:
            # Strategy 2: Extract host ID from page JSON data
            host_id_match = re.search(
                r'"hostId"\s*:\s*"?(\d+)"?', raw_html)
            if host_id_match:
                host_id = host_id_match.group(1)
                print(f"    ║ ✅ Host ID from JSON: {host_id}")
            else:
                print(f"    ║ ⚠ No host ID found anywhere on page.")

        if host_id:
            # Use /users/profile/ (NOT /users/show/ which redirects to login!)
            # Keep the PdpHomeMarketplace param — Airbnb expects it
            host_url = (f"https://www.airbnb.com.br/users/profile/{host_id}"
                        f"?previous_page_name=PdpHomeMarketplace")
            print(f"    ║ Navigating to: {host_url}")
            driver.get(host_url)
            time.sleep(8)

            # Check if we got redirected to login
            landed_url = driver.current_url
            if '/login' in landed_url:
                print(f"    ║ ⚠ Redirected to login! Trying alt URL...")
                # Try without params
                alt_url = f"https://www.airbnb.com.br/users/profile/{host_id}"
                driver.get(alt_url)
                time.sleep(8)
                landed_url = driver.current_url

            if '/login' not in landed_url:
                navigated_to_profile = True
                print(f"    ║ ✅ On profile: {landed_url[:80]}")
            else:
                print(f"    ║ ❌ Still on login page. Cannot access profile.")

        print(f"    ║ On host profile: {navigated_to_profile}")

        if navigated_to_profile:
            try:

                # Scroll progressively to trigger all lazy loads
                for scroll_pct in [0.3, 0.6, 1.0]:
                    driver.execute_script(
                        f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct});")
                    time.sleep(2)

                prof_html = driver.page_source
                prof_soup = BeautifulSoup(prof_html, 'html.parser')
                prof_text = prof_soup.get_text()

                # DEBUG: Show what the profile page actually says
                print(f"    ║ Profile page title: {driver.title}")
                print(f"    ║ Profile URL landed: {driver.current_url}")
                print(f"    ║ Profile text length: {len(prof_text)} chars")

                # Search for listing count keywords in the full text
                for keyword in ['anúncio', 'listing', 'acomodaç', 'place']:
                    idx = prof_text.lower().find(keyword)
                    if idx >= 0:
                        snippet = prof_text[max(0, idx-40):idx+60].strip()
                        print(f"    ║ Found '{keyword}' at pos {idx}: "
                              f"«{snippet}»")

                # Try multiple regex patterns
                patterns = [
                    (r'(\d+)\s*an[uú]ncios?', 'anúncios'),
                    (r'[Vv]er\s+(?:os\s+)?(\d+)', 'Ver os N'),
                    (r'[Ss]ee\s+all\s+(\d+)', 'See all N'),
                    (r'(\d+)\s+acomoda[çc]', 'acomodações'),
                    (r'(\d+)\s+places?\b', 'places'),
                    (r'(\d+)\s+listings?\b', 'listings'),
                    (r'[Ss]howing\s+(\d+)', 'Showing N'),
                ]

                portfolio_size = 1
                for pat, label in patterns:
                    m = re.search(pat, prof_text)
                    if m:
                        val = int(m.group(1))
                        if val > 1:  # Ignore "1 anúncio" (not useful)
                            portfolio_size = val
                            print(f"    ║ ✅ MATCH [{label}]: {val}")
                            break
                        else:
                            print(f"    ║ Match [{label}] = {val} (skipped, =1)")

                updates['host_portfolio_size'] = portfolio_size

                if portfolio_size <= 1:
                    # Last resort: count all /rooms/ links on profile
                    room_links = set()
                    for a in prof_soup.select('a[href*="/rooms/"]'):
                        room_links.add(a['href'].split('?')[0])
                    if len(room_links) > 1:
                        updates['host_portfolio_size'] = len(room_links)
                        print(f"    ║ Fallback: {len(room_links)} room links")
                    else:
                        print(f"    ║ ⚠ Portfolio still 1. No patterns matched.")

                print(f"    ║ Final portfolio_size: "
                      f"{updates['host_portfolio_size']}")

                # Scrape visible listing links from profile
                other_listings = []
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
                    host_block = (f"--- HOST_LISTINGS_JSON ---\n"
                                  f"{json.dumps(other_listings)}\n---")
                    updates['descricao'] = f"{host_block}\n\n{description}"
                    print(f"    ║ Cataloged {len(other_listings)} listings")

                # ─── CONTACT INFO EXTRACTION ───
                # Search profile text + listing description for contact info
                all_text = prof_text + "\n" + (description or "")

                # Email extraction
                emails_found = re.findall(
                    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
                    all_text)
                # Filter out airbnb internal emails
                real_emails = [
                    e for e in emails_found
                    if not any(x in e.lower() for x in [
                        'airbnb', 'noreply', 'example',
                        'test', 'luxuryrj', 'host_'
                    ])
                ]
                if real_emails:
                    updates['email'] = real_emails[0]
                    print(f"    ║ 📧 Email found: {real_emails[0]}")

                # Phone extraction (Brazilian formats)
                phones_found = re.findall(
                    r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[\-\s]?\d{4}',
                    all_text)
                if phones_found:
                    # Clean phone number
                    raw_phone = phones_found[0]
                    clean_phone = re.sub(r'[^\d+]', '', raw_phone)
                    if len(clean_phone) >= 10:
                        updates['telefone'] = clean_phone
                        print(f"    ║ 📞 Phone found: {clean_phone}")

                # Website / Instagram extraction from profile links
                contact_extras = {}
                for a_tag in prof_soup.select('a[href]'):
                    href = a_tag.get('href', '')
                    # Instagram
                    ig_match = re.search(
                        r'instagram\.com/([a-zA-Z0-9_.]+)', href)
                    if ig_match:
                        ig_handle = ig_match.group(1)
                        if ig_handle.lower() not in ['airbnb', 'p', 'reel']:
                            contact_extras['instagram'] = f"@{ig_handle}"
                            print(f"    ║ 📸 Instagram: @{ig_handle}")
                    # External website (not airbnb)
                    if ('http' in href and
                            'airbnb' not in href and
                            'google' not in href and
                            'facebook' not in href and
                            'instagram' not in href and
                            'apple' not in href and
                            'play.google' not in href):
                        contact_extras['website'] = href
                        print(f"    ║ 🌐 Website: {href}")

                # Also check profile text for Instagram handles
                ig_text = re.findall(r'@([a-zA-Z0-9_.]{3,30})', all_text)
                for handle in ig_text:
                    if handle.lower() not in [
                        'airbnb', 'gmail', 'hotmail', 'yahoo',
                        'outlook', 'icloud'
                    ] and 'instagram' not in contact_extras:
                        contact_extras['instagram'] = f"@{handle}"
                        print(f"    ║ 📸 Instagram (text): @{handle}")
                        break

                # Append contact extras to description as JSON
                if contact_extras:
                    contact_block = (f"\n--- CONTACT_INFO_JSON ---\n"
                                     f"{json.dumps(contact_extras)}\n---")
                    updates['descricao'] = (
                        updates.get('descricao', description or '')
                        + contact_block)

                # Check if we need Google Enrichment
                if not any(k in updates for k in ['email', 'telefone']) \
                        and not contact_extras and host_name:
                    
                    print(f"    ║ ⚠ No contact info on profile. Trying Google Enrichment for '{host_name}'...")
                    try:
                        # Open new tab for Google Search
                        driver.execute_script("window.open('');")
                        driver.switch_to.window(driver.window_handles[-1])
                        
                        search_query = f'"{host_name}" contato email telefone instagram rio de janeiro'
                        driver.get(f"https://www.google.com/search?q={search_query}")
                        time.sleep(3)
                        
                        g_text = driver.find_element("tag name", "body").text
                        
                        # Email via Google
                        g_emails = re.findall(
                            r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', g_text)
                        valid_g_emails = [e for e in g_emails if not any(x in e.lower() for x in ['google', 'airbnb', 'wix', 'domain'])]
                        if valid_g_emails:
                            updates['email'] = valid_g_emails[0]
                            print(f"    ║ 🎯 Google found email: {valid_g_emails[0]}")
                            
                        # Phone via Google
                        g_phones = re.findall(
                            r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[\-\s]?\d{4}', g_text)
                        if g_phones:
                            raw_p = g_phones[0]
                            clean_p = re.sub(r'[^\d+]', '', raw_p)
                            if len(clean_p) >= 10:
                                updates['telefone'] = clean_p
                                print(f"    ║ 🎯 Google found phone: {clean_p}")

                        # Instagram via Google
                        if 'instagram' not in contact_extras:
                            g_ig = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', g_text)
                            if g_ig:
                                handle = g_ig.group(1)
                                if handle.lower() not in ['airbnb', 'p', 'reel']:
                                    contact_extras['instagram'] = f"@{handle}"
                                    print(f"    ║ 🎯 Google found IG: @{handle}")
                                    
                        # Update description if extras found via Google
                        if contact_extras:
                             contact_block = (f"\n--- CONTACT_INFO_JSON ---\n"
                                             f"{json.dumps(contact_extras)}\n---")
                             updates['descricao'] = (
                                updates.get('descricao', description or '')
                                + contact_block)

                    except Exception as e:
                        print(f"    ║ ⚠ Google Enrichment failed: {e}")
                    finally:
                        # Close tab and return to profile
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])

                if not any(k in updates for k in ['email', 'telefone']) \
                        and not contact_extras:
                    print(f"    ║ ⚠ Still no contact info after Google search")

                driver.back()
                time.sleep(3)

            except Exception as he:
                print(f"    ║ ❌ Host profile error: {he}")
                import traceback
                traceback.print_exc()
                try: driver.back()
                except: pass
        else:
            print("    ║ Could not reach host profile page.")
            # Try to find count directly on listing page
            listing_count_match = re.search(
                r'(\d+)\s*an[uú]ncios?', soup.get_text())
            if listing_count_match:
                val = int(listing_count_match.group(1))
                updates['host_portfolio_size'] = val
                print(f"    ║ Found count on listing page: {val}")
            else:
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
                    print(f"    ║ Price: R$ {updates['preco_noite']}/night")
        except:
            pass

        # ─── Save ───
        supabase.table("leads").update(updates).eq("id", lead_id).execute()
        print(f"    ╚══ [DONE] Lead {lead_id} → 'ready'\n")

    except Exception as e:
        print(f"    ╚══ [ERROR] {e}")
        import traceback
        traceback.print_exc()
        supabase.table("leads").update(
            {"intelligence_status": "error"}
        ).eq("id", lead_id).execute()

# ──────────────────────────────────────────────
# SEARCH — Discover new leads from neighborhoods
# ──────────────────────────────────────────────
def scrape_main_leads():
    """Scrapes Airbnb search results for new leads."""
    print("--- Running Main Scraper ---")
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
    """Polls for 'pending' leads and deep-scrapes them."""
    print("\n🚀 [WATCHER] Scrape Engine ACTIVE.")
    print("Requests from your phone appear here.\n")

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
                    print("✅ Batch done. Waiting...\n")
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

    print(f"--- ZAI SCRAPER ENGINE: {mode.upper()} ---")

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
        print("\n⚡ Now deep-scraping all pending leads...")
        process_pending_once()

    elif "deep" in mode:
        process_pending_once()

    elif "watcher" in mode:
        start_watcher()

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: scraper.py [watcher|search|deep|<URL>]")
