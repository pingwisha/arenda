import asyncio
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

url = 'https://halooglasi.com/nekretnine/izdavanje-stanova/zvezdara-lipov-lad-ravanicka-3-0-60m2/5425643698544?kid=4'

def fetch(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='sr-RS',
        )
        page = context.new_page()
        page.goto(url, wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
        return html

html = fetch(url)
soup = BeautifulSoup(html, 'html.parser')

with open('halooglasi_detail.html', 'w', encoding='utf-8') as f:
    f.write(str(soup))

# Find price elements
price_selectors = ['.product-price', '.price', '.cena', '.listing-price', '.amount']
for selector in price_selectors:
    elements = soup.select(selector)
    if elements:
        print(f'Selector {selector}:')
        for el in elements[:5]:
            print(f'  {el.get_text(" ", strip=True)}')

# Find all text with EUR
text = soup.get_text(" ", strip=True)
lines = [line.strip() for line in text.split('\n') if '€' in line or 'eur' in line.lower()]
print('\nEUR lines:')
for line in lines[:20]:
    print(f'  {line}')
