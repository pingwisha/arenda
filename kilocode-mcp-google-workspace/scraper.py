from __future__ import annotations

import argparse
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

SITE_URLS = {
    "4zida.rs": "https://www.4zida.rs/izdavanje-stanova?jeftinije_od=890eur",
    "cityexpert.rs": "https://www.cityexpert.rs/izdavanje-stanova",
    "halooglasi.com": "https://www.halooglasi.com/nekretnine/izdavanje-stanova/beograd/trosoban?cena_d_to=900&cena_d_unit=4&namestenost_id_l=562",
    "imovina.net": "https://imovina.net/pretraga-nekretnina/izdavanje/?offerType%5B%5D=3&extras%5B%5D=35&mainRegion=1&subRegionText=&surfaceFrom=&surfaceTo=&priceFrom=&priceTo=900&currency=EUR&floorFrom=&floorTo=&sort=5&phone=&search=%D0%9F%D0%9E%D0%98%D0%A1%D0%9A&filterName=&filtersList=",
    "nekretnine.rs": "https://www.nekretnine.rs/izdavanje-stanova",
    "oglasi.rs": "https://www.oglasi.rs/nekretnine/izdavanje-stanova/beograd?pr%5Be%5D=900&pr%5Bc%5D=EUR&d%5BSobnost%5D%5B0%5D=Trosoban&d%5BOpremljenost%5D%5B0%5D=Name%C5%A1ten&d%5BInternet%5D=1",
}

FALLBACK_URLS = {
    "4zida.rs": "https://www.4zida.rs/izdavanje-stanova?jeftinije_od=890eur",
    "cityexpert.rs": "https://www.cityexpert.rs",
    "halooglasi.com": "https://www.halooglasi.com",
    "imovina.net": "https://www.imovina.net",
    "nekretnine.rs": "https://www.nekretnine.rs",
    "oglasi.rs": "https://www.oglasi.rs",
}

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


SITE_SELECTORS = {
    "default": {
        "cards": [
            "article",
            ".listing",
            ".offer",
            ".property-card",
            ".ad",
            ".item",
            "li",
            ".card",
        ],
        "title": ["h1", "h2", "h3", ".title", ".name", ".listing-title", ".property-title"],
        "price": [".price", ".cena", ".listing-price", ".amount", ".price-tag", ".price-value"],
    },
    "4zida.rs": {
        "cards": ["article", ".listing-item", ".property-card", ".offer-item"],
        "title": ["h2", ".title", ".listing-title", ".property-title"],
        "price": [".price", ".cena", ".listing-price", ".amount"],
    },
    "cityexpert.rs": {
        "cards": ["article", ".offer-item", ".property-card", ".listing-item"],
        "title": ["h2", ".title", ".name", ".listing-title"],
        "price": [".price", ".cena", ".listing-price"],
    },
    "halooglasi.com": {
        "cards": [".product-item", ".product-list-item", ".real-estates .product-item", "article", ".listing"],
        "title": [".product-title", ".title", "h3", "h2", ".listing-title"],
        "price": [".product-price", ".price", ".cena", ".listing-price", ".amount"],
    },
    "imovina.net": {
        "cards": ["article", ".listing-item", ".offer-item", ".ad"],
        "title": ["h2", ".title", ".listing-title", ".name"],
        "price": [".price", ".cena", ".listing-price", ".amount"],
    },
    "oglasi.rs": {
        "cards": [".advert_list_item_normalan", ".fpogl-holder", "article", ".listing-item"],
        "title": [".fpogl-list-title", "h2", ".title", ".listing-title", "h1"],
        "price": [".text-price", ".price", ".cena", ".listing-price"],
    },
}


def fetch_html(url: str, timeout: int = 20) -> str:
    candidates = []
    seen = set()

    def add_candidate(candidate: Optional[str]) -> None:
        if not candidate or candidate in seen:
            return
        seen.add(candidate)
        candidates.append(candidate)

    add_candidate(url)

    host = ""
    try:
        host = re.sub(r"^https?://", "", url).split("/", 1)[0]
    except Exception:
        host = ""

    if host:
        site_key = host.replace("www.", "")
        add_candidate(FALLBACK_URLS.get(site_key, ""))
        add_candidate(FALLBACK_URLS.get(host, ""))
        add_candidate(f"https://{host}")

    last_error: Optional[Exception] = None
    for candidate in candidates:
        try:
            response = requests.get(candidate, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if response.status_code < 400:
                return response.text
            last_error = requests.HTTPError(f"HTTP {response.status_code} for {candidate}")
        except requests.RequestException as exc:
            last_error = exc

    if last_error is not None:
        return ""
    return ""


def clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_price(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = clean_text(value)
    if not text:
        return None

    currency_matches = re.findall(r"(\d[\d\s.,]*)\s*(?:€|eur)", text, flags=re.IGNORECASE)
    if currency_matches:
        candidate = currency_matches[-1].replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(candidate)
        except ValueError:
            pass

    digits = re.findall(r"(\d+[\.,]?\d*)", text.replace("€", " "))
    if not digits:
        return None
    number = digits[-1].replace(".", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = re.sub(r"[^0-9]", "", clean_text(value))
    return int(text) if text else None


def safe_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = clean_text(value).lower()
    return any(token in text for token in ["da", "yes", "allow", "allowed", "true", "moguće", "1"])


def get_text_from_selectors(soup: BeautifulSoup, selectors: Iterable[str]) -> str:
    for selector in selectors:
        element = soup.select_one(selector)
        if element is not None:
            text = clean_text(element.get_text(" ", strip=True))
            if text:
                return text
    return ""


def absolute_url(site: str, href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    domain = "www.4zida.rs" if site == "4zida.rs" else site
    if href.startswith("/"):
        return f"https://{domain}{href}"
    return href


def is_real_listing_href(site: str, href: str) -> bool:
    if not href:
        return False
    href = href.strip()
    if href.startswith("http"):
        href = "/" + href.split("/", 3)[3] if "/" in href and len(href.split("/")) >= 4 else href

    if not href or href.startswith("#"):
        return False
    if any(href.lower().startswith(prefix) for prefix in ["javascript:", "mailto:", "tel:"]):
        return False

    clean = href.split("?", 1)[0].split("#", 1)[0].strip("/")
    if not clean:
        return False

    if site == "4zida.rs":
        if "izdavanje-stanova" not in href:
            return False
        parts = [p for p in href.split("/") if p]
        if len(parts) < 4:
            return False
        if parts[0] != "izdavanje-stanova":
            return False
        if any(part in {"beograd", "novi-sad", "nis", "subotica", "kragujevac", "zrenjanin", "pancevo", "zlatibor", "kopaonik", "kraljevo"} for part in parts[1:2]):
            return False
        last = parts[-1].lower()
        if len(last) < 10 or not re.fullmatch(r"[a-z0-9-]+", last):
            return False
        if not any(token in " ".join(parts).lower() for token in ["stan", "apartman", "studio", "jednosoban", "dvosoban"]):
            return False
        return True

    if site == "oglasi.rs":
        if "/oglas/" not in href:
            return False
        return True

    path = href.lower()
    if "/izdavanje-stanova/" in path:
        return "/izdavanje-stanova/" in path and not re.search(r"/izdavanje-stanova/(?:beograd|novi-sad|nis|subotica|kragujevac|zrenjanin|pancevo|zlatibor|kopaonik|kraljevo)(?:/|$)", path)
    return any(token in path for token in ["stan", "apartman", "listing", "offer", "oglas", "nekretnina"]) and not any(token in path for token in ["/kategorija", "/city", "/grad", "/search", "/filter"])


def infer_title_from_text(site: str, text: str) -> str:
    if site == "4zida.rs":
        cleaned = text
        cleaned = re.sub(r"(?i)\bPogledaj detaljnije\b|\bPrevious slide\b|\bNext slide\b|\bPremijum\b", " ", cleaned)
        price_match = re.search(r"(\d[\d\s.,]*)\s*(?:€|eur)", cleaned, flags=re.IGNORECASE)
        if price_match:
            cleaned = cleaned[:price_match.start()]
        cleaned = re.sub(r"(?i)\b(?:mesečno|mesecno|mjesecno|monthly|month)\b.*$", "", cleaned)
        cleaned = re.sub(r"^\s*\d+\s+", "", cleaned)
        cleaned = clean_text(cleaned)
        cleaned = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
        if len(cleaned) > 3:
            return cleaned
    return clean_text(text)[:200]


def find_listing_links(soup: BeautifulSoup, site: str) -> List[str]:
    links: List[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href in seen:
            continue
        normalized = href
        if href.startswith("http"):
            normalized = "/" + href.split("/", 3)[3] if "/" in href and len(href.split("/")) >= 4 else href
        if not is_real_listing_href(site, normalized):
            continue
        url = absolute_url(site, href)
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(url)

    return links


def enrich_listing_from_detail(raw: Dict[str, Any], site: str) -> Dict[str, Any]:
    url = (raw.get("url") or "").strip()
    if not url:
        return raw

    existing_title = (raw.get("title") or "").strip()
    existing_price = raw.get("price_raw")
    existing_text = (raw.get("source_text") or "").strip()

    if site == "halooglasi.com":
        try:
            from parsers.halooglasi import enrich_halooglasi_detail
            return enrich_halooglasi_detail(raw)
        except Exception:
            pass

    if site == "oglasi.rs":
        try:
            from parsers.oglasi import enrich_oglasi_detail
            return enrich_oglasi_detail(raw)
        except Exception:
            pass

    html = fetch_html(url)
    if not html:
        return raw

    soup = BeautifulSoup(html, "html.parser")
    site_config = SITE_SELECTORS.get(site, SITE_SELECTORS["default"])
    title_selectors = site_config.get("title", SITE_SELECTORS["default"]["title"])
    price_selectors = site_config.get("price", SITE_SELECTORS["default"]["price"])

    detail_text = clean_text(soup.get_text(" ", strip=True))
    title = get_text_from_selectors(soup, title_selectors)
    if not title and existing_title:
        title = existing_title
    price = get_text_from_selectors(soup, price_selectors) or existing_price

    if price:
        raw["price_raw"] = price
        raw["price_eur"] = parse_price(price)
    if title:
        raw["title"] = title
    if detail_text:
        raw["source_text"] = detail_text
    elif existing_text:
        raw["source_text"] = existing_text

    return raw


def extract_cards(html: str, site: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    site_config = SITE_SELECTORS.get(site, SITE_SELECTORS["default"])
    title_selectors = site_config.get("title", SITE_SELECTORS["default"]["title"])
    price_selectors = site_config.get("price", SITE_SELECTORS["default"]["price"])

    candidate_tags: List[Any] = []
    if site == "4zida.rs":
        links = find_listing_links(soup, site)
        for href in links:
            candidate_tags.append(soup.select_one(f'a[href="{href}"]') or soup)
    else:
        for selector in site_config.get("cards", SITE_SELECTORS["default"]["cards"]):
            candidate_tags.extend(soup.select(selector))

    if not candidate_tags:
        candidate_tags = [soup]

    seen: set[str] = set()
    seen_urls: set[str] = set()
    results: List[Dict[str, Any]] = []
    for tag in candidate_tags:
        container = tag
        if site == "4zida.rs" and tag.name == "a":
            for parent in tag.parents:
                if parent is None:
                    break
                parent_text = clean_text(parent.get_text(" ", strip=True))
                if len(parent_text) >= 30 and ("€" in parent_text or "soba" in parent_text.lower() or "premijum" in parent_text.lower()):
                    container = parent
                    break

        text = clean_text(container.get_text(" ", strip=True))
        if len(text) < 30:
            continue

        tag_key = str(container)
        if tag_key in seen:
            continue
        seen.add(tag_key)

        url = ""
        link = container.select_one("a[href]") or (tag.select_one("a[href]") if hasattr(tag, "select_one") else None)
        if link is not None:
            url = absolute_url(site, link.get("href", ""))

        if site == "4zida.rs":
            if not is_real_listing_href(site, url):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

        title = get_text_from_selectors(container, title_selectors)
        if not title:
            title = infer_title_from_text(site, text)
        if site == "4zida.rs" and title and re.search(r"\b(previous slide|next slide)\b", title, flags=re.IGNORECASE):
            continue
        price = get_text_from_selectors(container, price_selectors)
        if not price and "€" in text:
            match = re.search(r"(\d[\d\s.,]*)\s*(?:€|eur)", text, flags=re.IGNORECASE)
            if match:
                price = match.group(0)
        if site == "4zida.rs" and not price and text.lower().count("premijum"):
            continue

        card = {
            "site": site,
            "title": title,
            "price_raw": price,
            "price_eur": parse_price(price),
            "url": url,
            "source_text": text,
        }
        if url:
            card = enrich_listing_from_detail(card, site)
        results.append(card)

    return results


def _roman_to_int(roman: str) -> int:
    roman = roman.upper()
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for char in reversed(roman):
        value = values.get(char, 0)
        if value < prev:
            result -= value
        else:
            result += value
        prev = value
    return result if result > 0 else 0


def detect_rooms_count(text: str) -> int:
    if re.search(r"trosoban|trosavan|3-soban|3\s*soban|3\s*room", text, flags=re.IGNORECASE):
        return 3
    if re.search(r"dvosoban|2-soban|2\s*soban|2\s*room", text, flags=re.IGNORECASE):
        return 2
    if re.search(r"četvorosoban|4-soban|4\s*soban|4\s*room", text, flags=re.IGNORECASE):
        return 4
    if re.search(r"petosoban|5-soban|5\s*soban|5\s*room", text, flags=re.IGNORECASE):
        return 5

    match = re.search(r"(?:soba|sobe|room|rooms|spavaća soba|bedroom|bedrooms)\s*[:\s]*(\d+(?:[.,]\d+)?)", text, flags=re.IGNORECASE)
    if match:
        try:
            return int(float(match.group(1).replace(",", ".")))
        except ValueError:
            pass

    match = re.search(r"(\d+)\s*(?:soba|sobe|room|rooms|spavaća soba|bedroom|bedrooms)", text, flags=re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    match = re.search(r"-(\d)-", text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return 0


def normalize_listing(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = clean_text(raw.get("title") or "")
    price = parse_price(raw.get("price_raw"))
    text = (raw.get("source_text") or "").lower()
    url = (raw.get("url") or "").lower()

    rooms = detect_rooms_count(text)
    if not rooms:
        rooms = detect_rooms_count(url)
    if not rooms:
        rooms = detect_rooms_count(title)
    if not rooms and raw.get("site") == "halooglasi.com":
        rooms = 3

    has_pets = any(token in text for token in [
        "pasija", "pet", "pets", "dog", "cat", "sa psom", "sa mačkom",
        "kućni ljubimci", "psi", "mačke", "mace", "mogućnost sa psom"
    ])
    has_furniture = any(token in text for token in [
        "namešten", "namestena", "furniture", "mobili", "opremljen", "opremljena"
    ])
    has_washer = any(token in text for token in [
        "veš mašina", "washing machine", "washer", "perilica", "ves masina", "vešeraj"
    ])
    has_dishwasher = any(token in text for token in [
        "sudomašina", "dishwasher", "posudomachine", "suđa mašina", "sudomasina"
    ])
    has_kitchen = any(token in text for token in [
        "kuhinja", "kitchen", "kuhinja sa", "full kitchen", "odvojena kuhinja"
    ])

    price_text = raw.get("price_text") or raw.get("price_raw") or ""
    if not price_text and price:
        price_text = f"{price} EUR"

    return {
        "site": raw.get("site"),
        "title": title,
        "url": raw.get("url") or "",
        "price_eur": price,
        "price_text": price_text,
        "rooms_count": rooms,
        "pets_allowed": has_pets,
        "furnished": has_furniture,
        "washer_machine": has_washer,
        "dishwasher": has_dishwasher,
        "kitchen_separate": has_kitchen,
        "raw_text": text,
        "source_text": raw.get("source_text") or "",
        "is_match": False,
    }


def listing_matches(listing: Dict[str, Any]) -> bool:
    if listing.get("rooms_count", 0) < 3:
        return False
    if listing.get("price_eur") is None or listing["price_eur"] > 900:
        return False
    if not listing.get("pets_allowed"):
        return False
    if not listing.get("furnished"):
        return False
    if not listing.get("washer_machine"):
        return False
    if not listing.get("dishwasher"):
        return False
    if not listing.get("kitchen_separate"):
        return False
    return True


def listing_matches_lenient(listing: Dict[str, Any]) -> bool:
    if listing.get("rooms_count", 0) < 3:
        return False
    if listing.get("price_eur") is None or listing["price_eur"] > 900:
        return False
    if not listing.get("pets_allowed"):
        return False
    return True


def scrape_urls(urls: Iterable[str], site_hint: Optional[str] = None) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for url in urls:
        if not url:
            continue
        site = site_hint or re.sub(r"^https?://", "", url).split("/", 1)[0].replace("www.", "")
        html = fetch_html(url)
        if not html:
            continue
        card = {
            "site": site,
            "title": "",
            "price_raw": "",
            "price_eur": None,
            "url": url,
            "source_text": clean_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True)),
        }
        soup = BeautifulSoup(html, "html.parser")
        title = get_text_from_selectors(soup, SITE_SELECTORS.get(site, SITE_SELECTORS["default"]).get("title", SITE_SELECTORS["default"]["title"]))
        if not title:
            title = infer_title_from_text(site, card["source_text"])
        price = get_text_from_selectors(soup, SITE_SELECTORS.get(site, SITE_SELECTORS["default"]).get("price", SITE_SELECTORS["default"]["price"]))
        if not price and "€" in card["source_text"]:
            match = re.search(r"(\d[\d\s.,]*)\s*(?:€|eur)", card["source_text"], flags=re.IGNORECASE)
            if match:
                price = match.group(0)
        card["title"] = title or ""
        card["price_raw"] = price or ""
        card["price_eur"] = parse_price(price) if price else None
        normalized = normalize_listing(card)
        normalized["is_match"] = listing_matches(normalized)
        results.append(normalized)
    return results


def scrape_site(site_name: str) -> List[Dict[str, Any]]:
    if site_name == "airbnb.ru":
        try:
            from parsers.airbnb import parse_airbnb_site
            listings = parse_airbnb_site()
            return [
                {
                    "site": "airbnb.ru",
                    "title": l.title,
                    "url": l.url,
                    "price_text": f"{l.price_eur} EUR/ночь",
                    "price_eur": l.price_eur,
                    "price_raw": f"{l.price_eur} EUR",
                    "source_text": l.source_text,
                    "posted_date": "",
                    "rooms_count": l.rooms,
                    "pets_allowed": l.dogs_allowed or l.cats_allowed,
                    "furnished": True,
                    "washer_machine": l.washing_machine,
                    "dishwasher": l.dishwasher,
                    "kitchen_separate": l.kitchen,
                    "is_match": True,
                }
                for l in listings
            ]
        except Exception as exc:
            print(f"airbnb scrape error: {exc}")
            return []

    url = SITE_URLS.get(site_name, "")
    if not url:
        return []

    html = fetch_html(url)
    if not html:
        return []

    cards = extract_cards(html, site_name)
    normalized = [normalize_listing(item) for item in cards]
    detailed: List[Dict[str, Any]] = []
    for item in normalized:
        try:
            item = enrich_listing_from_detail(item, site_name)
        except Exception:
            pass
        detailed.append(item)
    return detailed


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect matching rental listings and print the results.")
    parser.add_argument("--site", choices=sorted(list(SITE_URLS.keys()) + ["airbnb.ru"]), help="Only process one source website")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of listings to print per site")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Google Sheets")
    args = parser.parse_args()

    sites = [args.site] if args.site else sorted(list(SITE_URLS.keys()) + ["airbnb.ru"])
    for site in sites:
        listings = scrape_site(site)[: args.limit]
        print(f"{site}: {len(listings)} listings scanned")
        for listing in listings:
            if listing.get("is_match"):
                print(f"MATCH -> {listing.get('title')} | {listing.get('price_eur')} EUR | rooms={listing.get('rooms_count')}")


if __name__ == "__main__":
    main()
