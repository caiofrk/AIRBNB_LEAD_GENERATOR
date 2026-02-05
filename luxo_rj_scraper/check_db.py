import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

supabase = create_client(url, key)

print(f"Testing connection to: {url}")
try:
    # Try to fetch from leads table
    res = supabase.table("leads").select("*").limit(1).execute()
    print("SUCCESS: Table 'leads' is configured and accessible.")
except Exception as e:
    print("\n--- DATABASE CONFIGURATION REQUIRED ---")
    if "relation \"public.leads\" does not exist" in str(e):
        print("The 'leads' table has not been created yet.")
    else:
        print(f"Error encountered: {e}")
    
    print("\nPlease go to your Supabase Dashboard (SQL Editor) and run this:")
    print("-" * 30)
    print("""
create table if not exists leads (
    id uuid primary key default gen_random_uuid(),
    anfitriao text,
    titulo text,
    link_imovel text,
    preco_noite int,
    bairro text,
    lat float8,
    lng float8,
    lux_score int,
    telefone text,
    email text,
    contatado boolean default false,
    criado_em timestamptz default now(),
    updated_at timestamptz default now()
);

-- IMPORTANT: Enable read access for the app
alter table leads enable row level security;
create policy "Allow public read" on leads for select using (true);
create policy "Allow public insert" on leads for insert with check (true);
create policy "Allow public update" on leads for update using (true);
""")
    print("-" * 30)
