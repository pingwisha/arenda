from __future__ import annotations

import asyncio
import re
import sys
from datetime import date
from typing import Any, Dict, List, Optional

from playwright.async_api import Page, async_playwright

from models.listing import Listing
from utils.extractor import extract_listing_data
from utils.translator import translate_listing


AIRBNB_SEARCH_URL = (
    "https://ru.airbnb.com/s/homes"
    "?adults=4&pets=2&min_beds=3&price_max=900"
    "&room_types%5B%5D=Entire%20home%2Fapt"
    "&location_search=NEARBY"
    "&ne_lat=44.95272015018647&sw_lat=44.69185421799102"
    "&ne_lng=20.786672112868843&sw_lng=20.262115088436275"
    "&monthly_start_date=2026-10-01&monthly_length=3&monthly_end_date=2027-01-01"
    "&search_by_map=true&min_beds=3&min_bathrooms=1"
    "&amenities%5B%5D=8&amenities%5B%5D=4"
    "&l2_property_type_ids%5B%5D=1&l2_property_type_ids%5B%5D=3"
    "&room_types%5B%5D=Entire%20home%2Fapt&price_max=900"
    "&price_filter_input_type=2&price_filter_num_nights=5"
    "&selected_filter_order%5B%5D=amenities%3A33"
    "&selected_filter_order%5B%5D=amenities%3A8"
    "&selected_filter_order%5B%5D=amenities%3A4"
    "&selected_filter_order%5B%5D=room_types%3AEntire%20home%2Fapt"
    "&selected_filter_order%5B%5D=price_max%3A900"
    "&selected_filter_order%5B%5D=min_beds%3A3"
    "&selected_filter_order%5B%5D=min_bathrooms%3A1"
    "&selected_filter_order%5B%5D=l2_property_type_ids%3A1"
    "&selected_filter_order%5B%5D=l2_property_type_ids%3A3"
    "&selected_filter_order%5B%5D=pets%3A2"
    "&zoom=10.969576034843326&search_type=filter_change&zoom_level=10"
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


async def _scroll_page(page: Page, max_scrolls: int = 2) -> None:
    for _ in range(max_scrolls):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(800)


def _extract_listing_id(url: str) -> str:
    match = re.search(r"/rooms/(\d+)", url)
    if match:
        return match.group(1)
    return url


def _parse_price_from_text(text: str) -> float:
    # 1) Prefer explicit nightly rate
    nightly_patterns = [
        r"(\d[\d\s.,]*)\s*(?:/ночь|/night|per night|за ночь|за сутки)",
    ]
    for pattern in nightly_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            try:
                value = float(match.replace(" ", "").replace(".", "").replace(",", "."))
                if value > 0:
                    return value
            except ValueError:
                pass

    # 2) If total price with night count is present, derive nightly rate
    total_pattern = r"(\d[\d\s.,]*)\s*(?:€|eur|EUR).*?(\d+)\s*(?:ночей|ночь|nights|night)"
    match = re.search(total_pattern, text, flags=re.IGNORECASE)
    if match:
        try:
            total = float(match.group(1).replace(" ", "").replace(".", "").replace(",", "."))
            nights = int(match.group(2))
            if total > 0 and nights > 0:
                return total / nights
        except (ValueError, IndexError):
            pass

    # 3) Fallback: smallest currency amount
    price_patterns = [
        r"(\d[\d\s.,]*)\s*(?:€|eur|EUR)",
        r"(\d[\d\s.,]*)\s*(?:₽|RUB|руб|рублей)",
        r"(\d[\d\s.,]*)\s*(?:\$|USD|доллар)",
    ]
    candidates = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            try:
                value = float(match.replace(" ", "").replace(".", "").replace(",", "."))
                if value > 0:
                    candidates.append(value)
            except ValueError:
                pass

    if not candidates:
        return 0.0

    candidates.sort()
    return candidates[0]


async def _parse_airbnb_listing_page(page: Page, url: str) -> Dict[str, Any]:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)
        await _scroll_page(page, max_scrolls=1)
    except Exception as exc:
        print(f"airbnb listing navigation error: {url} -> {exc}", file=sys.stderr)
        return {"site": "airbnb.ru", "title": "", "url": url, "price_raw": "", "price_eur": 0.0, "price_text": "", "posted_date": "", "source_text": ""}

    title = ""
    try:
        title = await page.title()
    except Exception:
        pass

    text = ""
    try:
        text = await page.evaluate("() => document.body.innerText")
    except Exception:
        text = ""

    description = ""
    try:
        description = await page.evaluate(
            """() => {
            const el = document.querySelector('[data-testid="property-description"]') || document.querySelector('#property_description') || document.querySelector('.description');
            return el ? el.innerText : '';
        }"""
        )
    except Exception:
        pass

    price = _parse_price_from_text(f"{title}\n{text}\n{description}")
    raw_text = f"{title}\n{text}\n{description}"

    price_text = ""
    posted_date = ""
    try:
        meta = await page.evaluate('''() => {
            const results = {};
            document.querySelectorAll('meta').forEach(el => {
                const prop = el.getAttribute('property') || '';
                const name = el.getAttribute('name') || '';
                const content = el.getAttribute('content') || '';
                if (prop.includes('price') || name.includes('price')) {
                    results.price = content;
                }
            });
            return results;
        }''')
        if meta.get("price"):
            price_text = str(meta["price"])
    except Exception:
        pass

    if not price_text:
        try:
            price_text = await page.evaluate('''() => {
                const selectors = [
                    '[data-testid="price"]',
                    '[class*="price"]',
                    '.price',
                    '.amount',
                    '[data-price]'
                ];
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.innerText && /\d/.test(el.innerText)) {
                        return el.innerText.trim().substring(0, 200);
                    }
                }
                return '';
            }''')
        except Exception:
            pass

    if not price_text and price:
        price_text = f"{price} EUR"

    return {
        "site": "airbnb.ru",
        "title": title,
        "url": url,
        "price_raw": price_text or (f"{price} EUR" if price else ""),
        "price_eur": price,
        "price_text": price_text,
        "posted_date": posted_date,
        "source_text": raw_text,
    }


async def _get_airbnb_listing_urls(page: Page) -> List[str]:
    try:
        await page.goto(AIRBNB_SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        await _scroll_page(page, max_scrolls=4)
    except Exception as exc:
        print(f"airbnb search navigation error: {exc}", file=sys.stderr)
        return []

    urls = await page.evaluate(
        """() => {
        const links = Array.from(document.querySelectorAll('a[href*="/rooms/"]'));
        return links.map(a => a.href).filter(href => href.includes('/rooms/'));
    }"""
    )
    
    seen_ids = set()
    unique = []
    for url in urls:
        listing_id = re.search(r"/rooms/(\d+)", url)
        if listing_id:
            lid = listing_id.group(1)
            if lid not in seen_ids:
                seen_ids.add(lid)
                unique.append(url)
    return unique


async def _parse_airbnb_site() -> List[Dict[str, Any]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="ru-RU",
        )
        page = await context.new_page()

        urls = await _get_airbnb_listing_urls(page)
        results = []
        for url in urls[:20]:
            try:
                raw = await _parse_airbnb_listing_page(page, url)
                if raw.get("price_eur") and raw["price_eur"] <= 900:
                    results.append(raw)
                await page.wait_for_timeout(800)
            except Exception as exc:
                print(f"airbnb parse error: {url} -> {exc}", file=sys.stderr)

        await browser.close()
        return results


def _parse_airbnb_detail(raw: Dict[str, Any]) -> Listing:
    data = extract_listing_data(raw)
    data["site"] = "airbnb.ru"
    data["property_type"] = "Квартира"
    rooms = data.get("rooms_count") or 0
    beds = data.get("beds_count") or 0
    if rooms < 3 and beds >= 3:
        rooms = beds
    data["rooms"] = rooms or 3
    data["kitchen"] = data.get("kitchen_separate") or data.get("kitchen") or False
    data["beds_for_all"] = data.get("beds_for_all") or True
    data["status"] = "Активно"
    today = date.today().isoformat()
    data["first_seen"] = today
    data["found_date"] = today
    data["last_updated"] = today
    data["current_price_eur"] = data.get("price_eur") or 0.0
    data["price_change_eur"] = 0.0

    return Listing(
        id=_extract_listing_id(data.get("url", "")),
        platform=data["site"],
        url=data.get("url", ""),
        title=data.get("title", ""),
        district=data.get("district", "Белград"),
        address=data.get("address", ""),
        property_type=data.get("property_type", "Квартира"),
        rooms=data.get("rooms", 3),
        kitchen=data.get("kitchen", False),
        area_m2=data.get("area_m2"),
        floor=data.get("floor", ""),
        price_eur=data.get("price_eur", 0.0),
        price_text=data.get("price_text", ""),
        currency="EUR",
        posted_date=data.get("posted_date", ""),
        utilities_eur=data.get("utilities_eur"),
        electricity_included=data.get("electricity_included"),
        deposit_eur=data.get("deposit_eur"),
        deposit_refundable=data.get("deposit_refundable", True),
        other_payments=data.get("other_payments", ""),
        total_cost_eur=data.get("total_cost_eur"),
        payment_3_weeks=data.get("payment_3_weeks", False),
        min_lease_months=data.get("min_lease_months", ""),
        dogs_allowed=data.get("pets_allowed", False),
        cats_allowed=data.get("pets_allowed", False),
        pet_fee_eur=data.get("pet_fee_eur", 0.0),
        fridge=data.get("fridge", False),
        stove=data.get("stove", False),
        oven=data.get("oven", False),
        washing_machine=data.get("washing_machine", False),
        dishwasher=data.get("dishwasher", False),
        hot_water=data.get("hot_water", False),
        wifi=data.get("wifi", False),
        beds_for_all=data.get("beds_for_all", False),
        furniture_desc=data.get("furniture_desc", ""),
        first_seen=date.fromisoformat(data["first_seen"]) if data.get("first_seen") else None,
        found_date=date.fromisoformat(data["found_date"]) if data.get("found_date") else None,
        last_updated=date.fromisoformat(data["last_updated"]) if data.get("last_updated") else None,
        rented_date=data.get("rented_date"),
        days_on_market=data.get("days_on_market", 0),
        current_price_eur=data.get("current_price_eur", 0.0),
        price_change_eur=data.get("price_change_eur", 0.0),
        status=data.get("status", "Активно"),
        notes=data.get("notes", ""),
        source_text=data.get("source_text", ""),
        raw=raw,
    )


def parse_airbnb_site() -> List[Listing]:
    try:
        if sys.version_info >= (3, 11):
            raw_list = asyncio.run(_parse_airbnb_site())
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            raw_list = loop.run_until_complete(_parse_airbnb_site())
            loop.close()
    except Exception as exc:
        print(f"airbnb parser failed: {exc}", file=sys.stderr)
        return []

    listings = []
    for raw in raw_list:
        try:
            translated = translate_listing(raw)
            listing = _parse_airbnb_detail(translated)
            listings.append(listing)
        except Exception as exc:
            print(f"airbnb normalize error: {exc}", file=sys.stderr)
    return listings
