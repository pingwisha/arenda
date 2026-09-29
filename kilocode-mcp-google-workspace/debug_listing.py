from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = 'https://www.4zida.rs/izdavanje-stanova/zrenjaninski-put-palilula-opstina-beograd/dvosoban-stan/668aee18ce9fe8976908ac15#standardni-opis'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(3000)
    html = page.content()
    browser.close()
soup = BeautifulSoup(html, 'html.parser')
text = soup.get_text(' ', strip=True)
print(text[2000:5000])
