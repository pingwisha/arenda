import re
import sys
import json
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE = Path(__file__).resolve().parent.parent


def load_requirements() -> Dict[str, Any]:
    must_have_path = WORKSPACE / "must_have.md"
    nice_to_have_path = WORKSPACE / "nice_to_have.md"

    def parse_md(path: Path) -> Dict[str, List[str]]:
        sections: Dict[str, List[str]] = {}
        current_section = ""
        if not path.exists():
            return sections
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                if line.startswith("## "):
                    current_section = line.lstrip("# ").strip()
                    sections[current_section] = []
                continue
            if line.startswith("- "):
                item = line[2:].strip()
                if current_section:
                    sections.setdefault(current_section, []).append(item)
        return sections

    return {
        "must_have": parse_md(must_have_path),
        "nice_to_have": parse_md(nice_to_have_path),
    }


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


def check_must_have(text: str) -> Dict[str, Any]:
    requirements = load_requirements()
    must_have = requirements.get("must_have", {})
    lower_text = text.lower()
    result: Dict[str, Any] = {"passed": True, "missing": [], "prohibited": [], "details": {}}

    prohibited_patterns = {
        "собака": ["не допускаются животные", "без животных", "zabranjeni ljubimci", "bez ljubimaca", "nije dozvoljeno sa ljubimcima", "ljubimci nisu dozvoljeni", "bez psa", "bez mačke"],
        "кот": ["не допускаются животные", "без животных", "zabranjeni ljubimci", "bez ljubimaca", "nije dozvoljeno sa ljubimcima", "ljubimci nisu dozvoljeni", "bez psa", "bez mačke"],
        "плита": ["нема плин", "нема шпора", "nema ploču", "no stove", "bez ploče"],
        "холодильник": ["нема фрижидера", "нема холодильник", "nema frižider", "no fridge"],
        "стиральная машина": ["нема веш машину", "nema veš mašinu", "no washing machine"],
        "горячая вода": ["нема топлу воду", "nema toplu vodu", "no hot water"],
        "wi-fi": ["нема wifi", "нема интернет", "nema wifi", "no wifi"],
    }

    for section, items in must_have.items():
        for item in items:
            keywords = [kw.strip().lower() for kw in item.split("/")]
            positive_hits = [kw for kw in keywords if kw and kw in lower_text]
            prohibition_hits = []
            for kw in keywords:
                for pat in prohibited_patterns.get(kw, []):
                    if pat in lower_text:
                        prohibition_hits.append(pat)
                        break

            if prohibition_hits:
                result["passed"] = False
                result["prohibited"].append(f"{section}: {item}")
                result["details"][f"{section}: {item}"] = "prohibited"
            elif positive_hits:
                result["details"][f"{section}: {item}"] = "present"
            else:
                result["details"][f"{section}: {item}"] = "unknown"
                result["missing"].append(f"{section}: {item}")
    return result


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

    must_have = check_must_have(text)
    extraction = extract_listing_info(text)

    if must_have["passed"] and extraction["missing_to_ask"]:
        message_status = "pending_approval"
    elif must_have["passed"]:
        message_status = "not_needed"
    else:
        message_status = "not_sent_must_have_failed"

    result = {
        "url": url,
        "must_have_passed": must_have["passed"],
        "missing_must_have": must_have["missing"],
        "prohibited_must_have": must_have["prohibited"],
        "unknown_must_have": must_have["missing"],
        "extracted_info": extraction["extracted"],
        "missing_to_ask": extraction["missing_to_ask"],
        "message_status": message_status,
        "draft_message": extraction.get("draft_message", ""),
        "notes": ["halooglasi legacy parser"],
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
