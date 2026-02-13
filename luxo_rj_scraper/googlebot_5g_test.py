"""
Trial 2-line trick: Googlebot User-Agent on 5G Mobile Connection.
"""
import requests
import re

LISTING_ID = "1026988231993117868"
HOST_ID = "92284964"

UA = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

headers = {
    'User-Agent': UA,
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}

print(f"--- Attempting Googlebot UA on Listing Page ({LISTING_ID}) ---")
r_listing = requests.get(f"https://www.airbnb.com.br/rooms/{LISTING_ID}", headers=headers)
print(f"Status Listing: {r_listing.status_code}")

print(f"--- Attempting Googlebot UA on Profile Page ({HOST_ID}) ---")
r_profile = requests.get(f"https://www.airbnb.com.br/users/show/{HOST_ID}", headers=headers)
print(f"Status Profile: {r_profile.status_code}")

all_text = r_listing.text + r_profile.text

# Use byte strings or handle encoding to avoid issues
print(f"Combined HTML length: {len(all_text)}")

emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', all_text)
real_emails = [e for e in emails if 'airbnb' not in e.lower()]
phones = re.findall(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[\-\s]?\d{4}', all_text)

print(f"Emails found: {real_emails}")
print(f"Phones found: {phones[:10]}")

if "host_profile" in all_text.lower():
    print("Found 'host_profile' keyword in HTML!")

with open("googlebot_5g.html", "w", encoding="utf-8") as f:
    f.write(all_text)
