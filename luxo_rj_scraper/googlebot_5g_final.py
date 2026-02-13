"""
Final attempt at '2-line trick' on 5G.
Use common headers that Googlebot actually uses.
"""
import requests
import re

LISTING_ID = "1592936909077567519"

headers = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

url = f"https://www.airbnb.com.br/rooms/{LISTING_ID}"

print(f"Requesting {url} as Googlebot on 5G...")
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    print(f"Page size: {len(r.text)}")
    
    # regex for hostId
    m = re.search(r'"hostId":\s*"(\d+)"', r.text)
    host_id = m.group(1) if m else "Not Found"
    print(f"Host ID found: {host_id}")
    
    # Search for contact
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', r.text)
    real_emails = [e for e in emails if 'airbnb' not in e.lower()]
    phones = re.findall(r'"\+?\d{10,15}"', r.text)
    
    print(f"Emails: {real_emails}")
    print(f"Phones: {phones}")
    
    if host_id != "Not Found":
        p_url = f"https://www.airbnb.com.br/users/show/{host_id}"
        print(f"Requesting Profile {p_url} as Googlebot...")
        rp = requests.get(p_url, headers=headers)
        print(f"Profile Status: {rp.status_code}")
        
        # Check profile
        p_emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', rp.text)
        p_real_emails = [e for e in p_emails if 'airbnb' not in e.lower()]
        print(f"Profile Emails: {p_real_emails}")

else:
    print(f"Error Body: {r.text[:500]}")
