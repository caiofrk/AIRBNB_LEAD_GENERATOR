import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

res = supabase.table("leads").select("bairro", count='exact').execute()
bairros = {}
for r in res.data:
    b = r['bairro']
    bairros[b] = bairros.get(b, 0) + 1

print("Leads per neighborhood:")
for b, count in sorted(bairros.items(), key=lambda x: x[1], reverse=True):
    print(f"- {b}: {count}")
