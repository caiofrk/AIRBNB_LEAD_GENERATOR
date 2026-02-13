"""
Plain requests call with high-quality Desktop UA on 5G.
Testing if it's just about the User-Agent being 'browser-like'.
"""
import requests
import re

LISTING_ID = "1592936909077567519"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Upgrade-Insecure-Requests': '1',
}

url = f"https://www.airbnb.com.br/rooms/{LISTING_ID}"

print(f"Requesting {url} as Desktop Chrome on 5G...")
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
    phones = re.findall(r'"\d{10,15}"', r.text)
    
    print(f"Emails: {real_emails}")
    print(f"Phones: {phones[:10]}")

else:
    print(f"Error: {r.status_code}")
    with open("error_5g.html", "w", encoding="utf-8") as f:
        f.write(r.text)
