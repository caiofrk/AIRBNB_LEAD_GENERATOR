import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key or "<" in url:
    print("Please configure .env with valid credentials.")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    print("Connected to Supabase.")
    print("Please run the following SQL in your Supabase SQL Editor:")
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
    """)
except Exception as e:
    print(f"Connection Error: {e}")
