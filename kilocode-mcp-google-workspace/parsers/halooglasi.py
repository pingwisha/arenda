from typing import Any, Dict
from ..listing_validator import fetch_page, is_cloudflare_blocked, load_requirements


def validate(url: str) -> Dict[str, Any]:
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
            item_prohibited = []
            for kw in keywords:
                for pat in prohibited_patterns.get(kw, []):
                    if pat in lower_text:
                        item_prohibited.append(pat)
                        break
            if item_prohibited:
                prohibited.append(f"{section}: {item}")
            elif not positive_hits:
                missing.append(f"{section}: {item}")
    passed = len(prohibited) == 0
    missing_to_ask = []
    draft_message = ""
    if passed and missing:
        questions = []
        if any("коммунал" in m.lower() or "utilities" in m.lower() for m in missing):
            questions.append("iznos komunala")
        if any("животн" in m.lower() or "pet" in m.lower() for m in missing):
            questions.append("da li je dozvoljeno sa psom i mackom, i da li postoji naknada za zivotinje")
        if questions:
            draft_message = (
                "Zdravo, interesuje me ovaj stan. Mozete li da odgovorite na par pitanja: "
                + ", ".join(questions)
                + "? Hvala unapred."
            )
            missing_to_ask = ["utilities_eur" if "коммунал" in " ".join(missing).lower() or "utilities" in " ".join(missing).lower() else None, "pet_fee_eur" if "животн" in " ".join(missing).lower() or "pet" in " ".join(missing).lower() else None]
            missing_to_ask = [m for m in missing_to_ask if m]
    return {
        "status": "ok",
        "site": "halooglasi.com",
        "url": url,
        "must_have_passed": passed,
        "missing_must_have": missing,
        "prohibited_must_have": prohibited,
        "extracted_info": {"text_snippet": text[:1000]},
        "missing_to_ask": missing_to_ask,
        "message_status": "pending_approval" if missing_to_ask else "not_needed",
        "draft_message": draft_message,
        "notes": ["halooglasi parser"],
    }
