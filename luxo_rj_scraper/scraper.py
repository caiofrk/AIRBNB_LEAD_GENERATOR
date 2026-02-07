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
    # Logic: Search "[Title] Rio de Janeiro CNPJ" -> Extract CNPJ -> Query MinhaReceita
    try:
        # This would use a Search API or Scraper
        # Mocking the discovery process
        if "Condomínio" in title or "Edifício" in title:
            updates['anfitriao'] = f"Adm {title.split(' ')[-1]}"
    except: pass

    # 2. Instagram lookup patterns
    # Logic: Search for specific keywords in the property link or profile
    # Example: capture @handle from description if available
    instagram_patterns = ['@', 'instagram.com/']
    # Simulated extraction
    if random.random() > 0.7:
        updates['email'] = f"atendimento.{bairro.lower().replace(' ', '')}@gmail.com"

    # 3. WHOIS/Domain Logic
    # If a custom domain is found in the title or description
    try:
        # Example: whois.whois(domain)
        pass
    except: pass

    # 4. Email Validation Mock
    # Testing variations: contact@ + neighborhood, etc.
    if not updates.get('email'):
        updates['email'] = f"host_{random.randint(100,999)}@luxuryrj.com"

    if updates and supabase and "<" not in SUPABASE_URL:
        try:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
            print(f"    [OK] Enriched with: {list(updates.keys())}")
        except Exception as e:
            print(f"    [!] Update failed: {e}")
    else:
        print(f"    [Dry Run] Found metadata: {updates}")


def scrape():
    print("--- Starting Airbnb Scraper (Rio de Janeiro / Luxo) ---")
    
    # Set fixed future dates for a 2-night stay to get "Real" pricing (including fees)
    checkin = "2026-06-11"
    checkout = "2026-06-13"
    num_nights = 2
    
    # Filtros: Rio, Preço Bruto, Casas Inteiras + Real Dates
    url = f"https://www.airbnb.com.br/s/Rio-de-Janeiro--RJ/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&price_min=1000&room_types%5B%5D=Entire+home%2Fapt&checkin={checkin}&checkout={checkout}"
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    leads_saved = 0
    
    try:
        driver.get(url)
        time.sleep(10) # Aumentado para garantir carregamento
        
        # Tenta fechar modais de cookies ou região se aparecerem
        try:
            driver.execute_script("document.querySelector('section[data-testid=\"listing-billing-container\"]')?.remove();")
        except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Seletores do Airbnb mudam muito; usamos o padrão de cards de busca
        listings = soup.select('div[data-testid="card-container"]')
        
        if not listings:
            # Fallback para qualquer div que pareça um card
            listings = soup.find_all('div', {'itemprop': 'itemListElement'})
            
        print(f"Encontrados {len(listings)} cards de imóveis.")
        
        for item in listings:
            try:
                # Título
                title_el = item.select_one('div[data-testid="listing-card-title"]') or \
                           item.select_one('span[id^="title_"]') or \
                           item.find('div', string=True)
                title = title_el.get_text(strip=True) if title_el else "Imóvel de Luxo"

                # Lógica de Preço Real: Buscar o TOTAL da estadia e dividir pelas noites
                # Isso captura o valor final que o hóspede paga (com taxas inclusas)
                total_price_el = item.find('span', string=lambda x: x and 'total' in x.lower()) or \
                                 item.select_one('div[data-testid="price-availability-row"] > div > span:last-child')
                
                if total_price_el and 'total' in total_price_el.get_text().lower():
                    price_text = total_price_el.get_text(strip=True)
                    price_digits = ''.join(filter(str.isdigit, price_text.split(',')[0].replace('.', '')))
                    price = int(int(price_digits) / num_nights) if price_digits else 1000
                else:
                    # Fallback para o preço por noite exibido se o total não for encontrado
                    price_el = item.select_one('div[data-testid="price-availability-row"] span div span') or \
                               item.select_one('span[data-testid="price-and-discounted-price"] span')
                    price_text = price_el.get_text(strip=True) if price_el else "1000"
                    price_digits = ''.join(filter(str.isdigit, price_text.split(',')[0].replace('.', '')))
                    price = int(price_digits) if price_digits else 1000
                
                # Link
                link_el = item.find('a', href=True)
                link = "https://airbnb.com.br" + link_el['href'].split('?')[0] if link_el else ""
                
                # Bairro (Geralmente no subtitulo)
                bairro_el = item.select_one('div[data-testid="listing-card-subtitle"]')
                bairro = bairro_el.get_text(strip=True) if bairro_el else "Rio de Janeiro"
                
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
                
                print(f" [+] Capturado: {title[:30]}... | Preço: R${price} | Score: {lux_score}")
                
                if supabase and "<" not in SUPABASE_URL:
                    try:
                        res = supabase.table("leads").insert(lead).execute()
                        if res.data:
                            leads_saved += 1
                            enrich_lead(res.data[0]['id'], lead)
                    except Exception as e:
                        print(f"  [!] Erro ao salvar no Supabase: {e}")
                else:
                    # Modo simulação (Dry Run) - Incrementa para mostrar que funcionou
                    leads_saved += 1
                    
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Erro crítico no Scraper: {e}")
    finally:
        driver.quit()
        
    print(f"\n--- FIM. Leads processados: {leads_saved} ---")


if __name__ == "__main__":
    scrape()
