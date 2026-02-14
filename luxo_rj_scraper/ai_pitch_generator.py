import os
import json
import time
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_pitch_logic(lead):
    """
    This is where the 'AI-agent' logic lives. 
    In a real-world scenario, this would call an LLM API.
    For this implementation, we use a sophisticated template system 
    that mimics personalized AI rephrasing based on maintenance items.
    """
    anfitriao = lead.get('anfitriao') or 'Parceiro'
    titulo = lead.get('titulo') or 'seu imóvel'
    maintenance = lead.get('maintenance_items') or []
    gap = lead.get('cleanliness_gap')
    
    # Base segments for different maintenance items
    maint_segments = {
        'Mármore/Vidro': "Notei que seu imóvel possui superfícies nobres como mármore e vidros amplos, que exigem um cuidado especializado para manter o brilho e a sofisticação que seus hóspedes esperam.",
        'Piscina/Jacuzzi': "Como sua propriedade oferece o diferencial de piscina/jacuzzi, sabemos que a manutenção impecável desses itens é o que separa um comentário 5 estrelas de uma reclamação sobre higiene.",
        'Automação': "Vi que você investiu em automação e tecnologia. Esse tipo de setup exige uma equipe que entenda de cuidados técnicos para não comprometer os sistemas durante a operação.",
        'Café Premium': "O capricho com mimos como café premium mostra que você preza pela experiência. Nossa gestão foca em elevar esse padrão em todos os pontos de contato."
    }
    
    selected_segments = [maint_segments[m] for m in maintenance if m in maint_segments]
    
    # Cleanliness Gap handling
    gap_segment = ""
    if gap:
        gap_segment = f"Vi alguns comentários sobre a limpeza (mencionaram: {gap}). Em locações de alto padrão, esses detalhes impactam diretamente seu ranking e preço médio. Podemos resolver isso definitivamente."
    else:
        gap_segment = "Seu imóvel tem um potencial incrível para o mercado de ultra-luxo, e uma gestão operacional de precisão pode ajudar a maximizar seu retorno."

    # Combine into a unique pitch
    pitch = f"Olá {anfitriao}! Tudo bem?\n\n"
    pitch += f"Estava analisando o perfil do seu imóvel '{titulo}' e fiquei impressionado com o padrão. "
    
    if selected_segments:
        pitch += " ".join(selected_segments) + " "
    
    pitch += f"\n\n{gap_segment}\n\n"
    pitch += "Trabalhamos com consultoria e gestão operacional focada exatamente nesse nível de exigência. Gostaria de agendar uma breve conversa ou uma visita técnica sem compromisso?\n\nNo aguardo!"
    
    return pitch

def process_leads():
    print("🚀 AI Pitch Generator starting...")
    
    # Fetch leads that are 'ready' but don't have a personalized pitch yet
    # We'll check if the 'descricao' already contains the AI block
    response = supabase.table("leads").select("*").eq("intelligence_status", "ready").execute()
    leads = response.data
    
    print(f"Found {len(leads)} leads to process.")
    
    updated_count = 0
    for lead in leads:
        desc = lead.get('descricao') or ""
        
        # Skip if already has AI Intel
        if "--- AI_INTEL_JSON ---" in desc:
            continue
            
        print(f"  Generating pitch for: {lead.get('anfitriao')} ({lead.get('id')})")
        
        pitch = generate_pitch_logic(lead)
        
        # Create the AI Intel JSON
        luxury_val = lead.get('lux_score') or 0
        ai_intel = {
            "luxury": float(luxury_val) / 100.0,
            "wa_hook": pitch,
            "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Inject into description
        new_desc = desc + f"\n\n--- AI_INTEL_JSON ---\n{json.dumps(ai_intel, indent=2)}\n---"
        
        # Update Supabase
        supabase.table("leads").update({
            "descricao": new_desc
        }).eq("id", lead['id']).execute()
        
        updated_count += 1
        time.sleep(0.5) # Avoid hitting limits
        
    print(f"✅ Finished! Updated {updated_count} leads with unique AI pitches.")

if __name__ == "__main__":
    process_leads()
