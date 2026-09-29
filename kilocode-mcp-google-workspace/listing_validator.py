import json
import re
import sys
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


def detect_site(url: str) -> str:
    for domain in ["halooglasi.com", "4zida.rs", "cityexpert.rs", "imovina.net", "nekretnine.rs", "oglasi.rs", "airbnb.com"]:
        if domain in url:
            return domain
    return ""


def validate_generic(url: str) -> Dict[str, Any]:
    html = fetch_page(url)
    if is_cloudflare_blocked(html):
        return {"status": "blocked_by_cloudflare", "url": url}
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    requirements = load_requirements()
    must_have = requirements.get("must_have", {})
    lower_text = text.lower()
    missing = []
    prohibited = []
    prohibited_patterns = {
        "собака": ["не допускаются животные", "без животных", "zabranjeni ljubimci", "bez ljubimaca", "nije dozvoljeno sa ljubimcima", "ljubimci nisu dozvoljeni", "bez psa", "bez mačke"],
        "кот": ["не допускаются животные", "без животных", "zabranjeni ljubimci", "bez ljubimaca", "nije dozvoljeno sa ljubimcima", "ljubimci nisu dozvoljeni", "bez psa", "bez mačke"],
        "плита": ["нема плин", "нема шпора", "nema ploču", "no stove", "bez ploče", "nema šporet", "nema rernu"],
        "холодильник": ["нема фрижидера", "нема холодильник", "nema frižider", "no fridge", "nema frizider"],
        "стиральная машина": ["нема веш машину", "nema veš mašinu", "no washing machine", "nema ves masinu"],
        "горячая вода": ["нема топлу воду", "nema toplu vodu", "no hot water"],
        "wi-fi": ["нема wifi", "нема интернет", "nema wifi", "no wifi"],
    }
    for section, items in must_have.items():
        for item in items:
            keywords = [kw.strip().lower() for kw in item.split("/")]
            extended_keywords = list(keywords)
            for kw in keywords:
                if kw == "плита":
                    extended_keywords.extend(["šporet", "rerna", "ploča", "plita", "kuhinjski elementi"])
                elif kw == "холодильник":
                    extended_keywords.extend(["frižider", "frizider", "zamrzivač"])
                elif kw == "стиральная машина":
                    extended_keywords.extend(["veš mašina", "ves mašina", "ves masina"])
                elif kw == "горячая вода":
                    extended_keywords.extend(["topla voda", "topla vode"])
                elif kw == "wi-fi":
                    extended_keywords.extend(["wifi", "internet", "bežični"])
                elif kw == "собака":
                    extended_keywords.extend(["psa", "psi", "pas", "kućni ljubimci", "ljubimci"])
                elif kw == "кот":
                    extended_keywords.extend(["mačka", "mačke", "macka", "kućni ljubimci", "ljubimci"])
                elif kw == "Белград":
                    extended_keywords.extend(["beograd", "belgrade"])
            if any(kw in lower_text for kw in extended_keywords if kw):
                continue
            item_prohibited = []
            for kw in keywords:
                for pat in prohibited_patterns.get(kw, []):
                    if pat in lower_text:
                        item_prohibited.append(pat)
                        break
            if item_prohibited:
                prohibited.append(f"{section}: {item}")
            elif section == "Разрешены животные":
                pass
            else:
                missing.append(f"{section}: {item}")
    passed = len(prohibited) == 0
    missing_to_ask = []
    draft_message = ""
    if passed and missing:
        questions = []
        if any("коммунал" in m.lower() or "utilities" in m.lower() for m in missing):
            questions.append("iznos komunala")
        if any("постел" in m.lower() or "bed" in m.lower() or "лежај" in m.lower() for m in missing):
            questions.append("da li postoji lezaj ili krevet u sobi")
        appliance_questions = []
        if any("плита" in m.lower() or "stove" in m.lower() for m in missing):
            appliance_questions.append("plin/sporet")
        if any("холодильник" in m.lower() or "fridge" in m.lower() for m in missing):
            appliance_questions.append("frižider")
        if any("стиральная машина" in m.lower() or "washing machine" in m.lower() for m in missing):
            appliance_questions.append("veš mašina")
        if any("горячая вода" in m.lower() or "hot water" in m.lower() for m in missing):
            appliance_questions.append("topla voda")
        if any("wi-fi" in m.lower() or "wifi" in m.lower() for m in missing):
            appliance_questions.append("wi-fi/internet")
        if appliance_questions:
            questions.append("da li postoji " + ", ".join(appliance_questions))
        if questions:
            draft_message = (
                "Zdravo, interesuje me ovaj stan. Mozete li da odgovorite na par pitanja: "
                + ", ".join(questions)
                + "? Hvala unapred."
            )
            missing_to_ask = ["utilities_eur" if any("коммунал" in m.lower() or "utilities" in m.lower() for m in missing) else None]
            if any("постел" in m.lower() or "bed" in m.lower() or "лежај" in m.lower() for m in missing):
                missing_to_ask.append("beds_info")
            if appliance_questions:
                missing_to_ask.append("appliances_info")
            missing_to_ask = [m for m in missing_to_ask if m]
    if passed and not missing_to_ask:
        if not any(kw in lower_text for kw in ["ležaj", "krev", "bed", "спаваћа", "spavaća", "gostinska", "dnevna", "sobe", "sobnost"]):
            missing_to_ask.append("beds_info")
            if not draft_message:
                draft_message = "Zdravo, interesuje me ovaj stan. Mozete li da odgovorite na par pitanja: da li postoji lezaj ili krevet u sobi? Hvala unapred."
            elif "da li postoji lezaj ili krevet u sobi" not in draft_message:
                draft_message = draft_message[:-1] + ", da li postoji lezaj ili krevet u sobi? Hvala unapred."
    return {
        "status": "ok",
        "site": detect_site(url),
        "url": url,
        "must_have_passed": passed,
        "missing_must_have": missing,
        "prohibited_must_have": prohibited,
        "extracted_info": {"text_snippet": text[:1000]},
        "missing_to_ask": missing_to_ask,
        "message_status": "pending_approval" if missing_to_ask else "not_needed",
        "draft_message": draft_message,
        "notes": ["generic validation only"],
    }


def validate_listing(url: str) -> Dict[str, Any]:
    site = detect_site(url)
    if site == "halooglasi.com":
        try:
            import subprocess, json
            script = Path(__file__).with_name("listing_validator_legacy.py")
            proc = subprocess.run(
                ["python", str(script), url],
                capture_output=True,
                text=True,
                check=False,
            )
            candidates = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{") or line.strip().startswith("[")]
            if candidates:
                data = json.loads(candidates[-1])
                if isinstance(data, dict):
                    return data
            return {"status": "error", "site": site, "url": url, "error": proc.stderr or proc.stdout}
        except Exception as exc:
            return {"status": "error", "site": site, "url": url, "error": str(exc)}
    return validate_generic(url)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python listing_validator.py <listing_url>")
        return 1
    url = sys.argv[1]
    result = validate_listing(url)
    try:
        print(json.dumps(result, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("status") != "blocked_by_cloudflare" else 2


if __name__ == "__main__":
    raise SystemExit(main())
