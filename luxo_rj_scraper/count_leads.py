import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

res = supabase.table("leads").select("*", count='exact').execute()
print(f"Total leads in database: {res.count}")

# Print count by status
pending = supabase.table("leads").select("*", count='exact').eq("intelligence_status", "pending").execute()
ready = supabase.table("leads").select("*", count='exact').eq("intelligence_status", "ready").execute()
error = supabase.table("leads").select("*", count='exact').eq("intelligence_status", "error").execute()

print(f"Pending: {pending.count}")
print(f"Ready: {ready.count}")
print(f"Error: {error.count}")
