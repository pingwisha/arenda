from __future__ import annotations

import re
from typing import Any, Dict

from playwright.sync_api import sync_playwright

from scraper import clean_text, parse_price


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _fetch_with_playwright(url: str, timeout: int = 45000) -> str:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 800}, locale="sr-RS")
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return ""


def enrich_oglasi_detail(raw: Dict[str, Any]) -> Dict[str, Any]:
    url = (raw.get("url") or "").strip()
    if not url:
        return raw

    html = _fetch_with_playwright(url)
    if not html:
        return raw

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    try:
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
    except Exception:
        pass

    description = ""
    try:
        desc = soup.select_one(".oglas-description, #description, .description")
        if desc:
            description = clean_text(desc.get_text(" ", strip=True))
    except Exception:
        pass

    full_text = clean_text(soup.get_text(" ", strip=True))
    if not description:
        description = full_text

    combined_text = f"{title} {description} {full_text}"

    if title and not raw.get("title"):
        raw["title"] = title
    if combined_text:
        raw["source_text"] = combined_text

    price_text = raw.get("price_text") or raw.get("price_raw") or ""
    if not price_text:
        price_match = re.search(r"(\d[\d\s.,]*)\s*(?:€|eur)", combined_text, flags=re.IGNORECASE)
        if price_match:
            price_text = price_match.group(0)
            raw["price_text"] = price_text
            raw["price_eur"] = parse_price(price_text)
    elif not raw.get("price_eur"):
        raw["price_eur"] = parse_price(price_text)

    posted_match = re.search(
        r"(?:objavljen|posted|датум|datum|datum objave| Kreirano|objavljeno)[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d{2}-\d{2})",
        combined_text,
        flags=re.IGNORECASE,
    )
    if posted_match:
        raw["posted_date"] = posted_match.group(1)

    return raw
