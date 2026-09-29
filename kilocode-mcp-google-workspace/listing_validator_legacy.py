from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

WORKSPACE = Path(__file__).resolve().parent.parent

from requirements import Requirements, validate_requirements, _build_draft_message


def fetch_page(url: str, timeout: int = 20000) -> str:
    try:
        from playwright.sync_api import sync_playwright
        USER_AGENT = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="sr-RS",
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(1500)
            html = page.content()
            browser.close()
            return html
    except Exception as exc:
        print(f"Fetch error: {exc}")
        return ""


def is_cloudflare_blocked(html: str) -> bool:
    if not html:
        return True
    lower = html.lower()
    return any(phrase in lower for phrase in [
        "выполнение проверки безопасности",
        "checking your browser",
        "идёт проверка",
        "проверка, что вы не бот",
    ])


def extract_listing_info(text: str) -> Dict[str, Any]:
    lower_text = text.lower()
    info: Dict[str, Any] = {}

    def find_pattern(patterns: List[str], default: Any = None) -> Any:
        for pattern in patterns:
            match = re.search(pattern, lower_text)
            if match:
                return match.group(1).strip() if match.lastindex else match.group(0).strip()
        return default

    info["price_eur"] = find_pattern([
        r"(\d{2,5})\s*(?:eur|€|евро)",
        r"цена[:\s]*(\d{2,5})",
    ])
    info["area_m2"] = find_pattern([
        r"(\d{1,2}(?:[.,]\d+)?)\s*(?:m²|кв\.?м|m2)",
    ])
    info["rooms"] = find_pattern([
        r"(\d)\s*(?:соб(a|е)|биност|room|sob[a-z]*)",
    ])
    info["floor"] = find_pattern([
        r"(\d+/\d+)\s*?этаж",
        r"floor[:\s]*(\d+/\d+)",
    ])
    info["fridge"] = any(kw in lower_text for kw in ["фрижидер", "холодильник", "фриж", "fridge", "frižider", "fri zider"])
    info["stove"] = any(kw in lower_text for kw in ["плин", "шпора", "стова", "stove", "пчекањ", "kuhinjska ploča", "šporhet"])
    info["washing_machine"] = any(kw in lower_text for kw in ["ves mašina", "washing machine", "стиральная машина", "ves masina", "ves-masina"])
    info["hot_water"] = any(kw in lower_text for kw in ["topla voda", "topla vode", "hot water", "горячая вода", "topla-voda"])
    info["wifi"] = any(kw in lower_text for kw in ["wi-fi", "wifi", "wireless", "интернет", "internet"])
    info["dogs_allowed"] = any(kw in lower_text for kw in ["дозвољен|допуска|дозвољени пси", "собака|пси|дозвољен пас", "псе", "pas", "psi", "дозвољен за псе", "допускају се пси"])
    info["cats_allowed"] = any(kw in lower_text for kw in ["мачка", "кошка", "мачке", "macka", "mačka", "дозвољен за мачке", "допускају се мачке"])
    info["utilities_mentioned"] = any(kw in lower_text for kw in ["комунал", "utilities", "žiranje", "режи", "општина", "komunale", "komunal"])
    info["deposit_mentioned"] = any(kw in lower_text for kw in ["депозит", "depozit", "zalog", "залог"])
    info["pet_fee_mentioned"] = any(kw in lower_text for kw in ["попуст за животиње", "naknada za zivotinje", "доплата за живот"])

    missing = []
    if not info.get("utilities_mentioned"):
        missing.append("utilities_eur")
    if not info.get("deposit_mentioned"):
        missing.append("deposit_eur")
    if not info.get("pet_fee_mentioned"):
        missing.append("pet_fee_eur")

    draft_message = ""
    if missing:
        questions = []
        if "utilities_eur" in missing:
            questions.append("iznos komunala")
        if "deposit_eur" in missing:
            questions.append("depozit i uslovi povlacenja depozita")
        if "pet_fee_eur" in missing:
            questions.append("da li je dozvoljeno sa psom i mackom, i da li postoji naknada za zivotinje")
        draft_message = (
            "Zdravo, interesuje me ovaj stan. Mozete li da odgovorite na par pitanja: "
            + ", ".join(questions)
            + "? Hvala unapred."
        )

    return {"extracted": info, "missing_to_ask": missing, "draft_message": draft_message}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python listing_validator_legacy.py <listing_url>")
        return 1

    url = sys.argv[1]
    print(f"Fetching listing: {url}")
    html = fetch_page(url)

    if is_cloudflare_blocked(html):
        result = {
            "status": "blocked_by_cloudflare",
            "url": url,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 2

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    validation = validate_requirements(text)
    extraction = extract_listing_info(text)

    missing_must = validation["missing_must_have"]
    missing_nice = validation["missing_nice_to_have"]
    prohibited = validation["prohibited"]
    passed = len(prohibited) == 0

    missing_to_ask = []
    draft_message = ""
    if passed and (missing_must or missing_nice):
        draft_message, missing_to_ask = _build_draft_message(missing_must, missing_nice, "halooglasi.com")

    if missing_to_ask:
        message_status = "pending_approval"
    elif passed:
        message_status = "not_needed"
    else:
        message_status = "not_sent_must_have_failed"

    result = {
        "url": url,
        "must_have_passed": passed,
        "missing_must_have": [f"{m['section']}: {m['item']}" for m in missing_must],
        "prohibited_must_have": [f"{m['section']}: {m['item']}" for m in prohibited],
        "unknown_must_have": [f"{m['section']}: {m['item']}" for m in missing_must],
        "extracted_info": extraction["extracted"],
        "missing_to_ask": missing_to_ask,
        "message_status": message_status,
        "draft_message": draft_message,
        "notes": ["halooglasi legacy parser"],
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
