import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_validator(url: str) -> dict:
    script = Path(__file__).with_name("listing_validator_legacy.py")
    proc = subprocess.run(
        [sys.executable, str(script), url],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    raise RuntimeError(proc.stderr or proc.stdout)


def run_review(raw_listing_text: str, draft_questions: list[str]) -> dict:
    redundant = []
    missing = list(draft_questions)
    contradictions = []
    lower = raw_listing_text.lower()

    checks = [
        ("kuhinja", ["kuhinja", "plin", "sporet", "rerna"]),
        ("frižider", ["frižider", "frizider", "zamrzivač"]),
        ("wi-fi", ["wi-fi", "wifi", "internet", "bežični"]),
        ("topla voda", ["topla voda", "topla vode"]),
        ("veš mašina", ["veš mašina", "ves mašina", "ves masina"]),
        ("sudomašina", ["sudomašina", "sudomasina", "posudomachine"]),
        ("krevet", ["krevet", "lezaj", "kreveta", "ležaj"]),
        ("psa", ["psa", "psi", "pas", "kućni ljubimci"]),
        ("mačkom", ["mačka", "mačke", "macka", "кошка"]),
    ]

    for q in draft_questions:
        removed = False
        for keyword, patterns in checks:
            if keyword in q:
                if any(p in lower for p in patterns):
                    redundant.append(q)
                    missing.remove(q)
                    removed = True
                    break
        if not removed:
            q_lower = q.lower()
            if any(p in q_lower for p in ["nema ", "bez ", "no "]):
                for keyword, patterns in checks:
                    if keyword in q:
                        if any(("nema " + p) in lower or ("bez " + p) in lower or ("no " + p) in lower for p in patterns):
                            contradictions.append(q)
                            missing.remove(q)
                            break

    return {
        "approved": True,
        "redundant_questions": redundant,
        "missing_questions": missing,
        "contradictions": contradictions,
        "recommended_draft_questions": missing,
        "recommended_message_status": "pending_approval" if missing else "not_needed",
    }


TRANSLATIONS = {
    "da li postoji kuhinja i plin/sporet": {
        "ru": "есть ли кухня и плита/газовая поверхность",
        "en": "is there a kitchen and stove",
    },
    "da li postoji frižider": {
        "ru": "есть ли холодильник",
        "en": "is there a fridge",
    },
    "da li postoji wi-fi ili internet": {
        "ru": "есть ли wi-fi или интернет",
        "en": "is there wifi or internet",
    },
    "da li postoji topla voda": {
        "ru": "есть ли горячая вода",
        "en": "is there hot water",
    },
    "da li postoji veš mašina": {
        "ru": "есть ли стиральная машина",
        "en": "is there a washing machine",
    },
    "da li postoji sudomašina": {
        "ru": "есть ли посудомоечная машина",
        "en": "is there a dishwasher",
    },
    "koliko spavaci sobe ima": {
        "ru": "сколько спален",
        "en": "how many bedrooms",
    },
    "da li postoji lezaj ili krevet za sve osobe": {
        "ru": "есть ли кровать для всех",
        "en": "is there a bed for everyone",
    },
    "da li je dozvoljeno sa psom": {
        "ru": "разрешена ли собака",
        "en": "is a dog allowed",
    },
    "da li je dozvoljeno sa mačkom": {
        "ru": "разрешена ли кошка",
        "en": "is a cat allowed",
    },
    "iznos komunala": {
        "ru": "сумма коммунальных платежей",
        "en": "utilities amount",
    },
}


def translate_questions(questions: list[str], lang: str) -> list[str]:
    translated = []
    for q in questions:
        if q in TRANSLATIONS and lang in TRANSLATIONS[q]:
            translated.append(TRANSLATIONS[q][lang])
        else:
            translated.append(q)
    return translated


def build_message(questions: list[str], lang: str) -> str:
    if lang == "sr":
        intro = "Zdravo, interesuje me ovaj stan. Mozete li da odgovorite na par pitanja:"
        outro = "Hvala unapred."
    elif lang == "ru":
        intro = "Здравствуйте, меня интересует эта квартира. Не могли бы вы ответить на несколько вопросов:"
        outro = "Спасибо заранее."
    else:
        intro = "Hello, I am interested in this apartment. Could you answer a few questions:"
        outro = "Thank you in advance."

    translated = translate_questions(questions, lang)
    return f"{intro} {', '.join(translated)}? {outro}"


def save_report(result: dict, review: dict):
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = Path(f"{date_str}.md")

    recommended = review.get("recommended_draft_questions", [])
    if not recommended:
        return None

    block = f"## Объявление\n- Ссылка: {result['url']}\n\n## Есть\n"
    for item in result.get("present_items", []):
        block += f"- {item}\n"
    block += "\n## Нет\n"
    for item in result.get("prohibited_must_have", []):
        block += f"- {item}\n"
    block += "\n## Неизвестно\n"
    for item in result.get("missing_must_have", []):
        block += f"- {item}\n"
    block += "\n## Сообщение\n"
    block += "### Русский\n" + build_message(recommended, "ru") + "\n\n"
    block += "### Srpski\n" + build_message(recommended, "sr") + "\n\n"
    block += "### English\n" + build_message(recommended, "en") + "\n"

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        if content.strip() and not content.endswith("\n\n"):
            content += "\n"
        content += "\n--------------------------------------------------------------------------------------------------------------\n\n" + block
    else:
        content = f"# {date_str}\n\n" + block

    file_path.write_text(content, encoding="utf-8")
    return file_path


def main():
    url = "https://www.halooglasi.com/nekretnine/izdavanje-stanova/stan-50-m2/5425646140238?kid=1"
    result = run_validator(url)
    if result.get("status") == "blocked_by_cloudflare":
        print(json.dumps({"status": "blocked"}, ensure_ascii=False))
        return
    review = run_review(result.get("raw_listing_text", ""), result.get("draft_questions", []))
    if not review["approved"]:
        print(json.dumps({"status": "review_rejected", "review": review}, ensure_ascii=False))
        return
    file_path = save_report(result, review)
    if file_path is None:
        print(json.dumps({"status": "not_needed"}, ensure_ascii=False))
    else:
        output = json.dumps({"status": "saved_to_file", "file": str(file_path), "review": review}, ensure_ascii=False)
        try:
            print(output)
        except UnicodeEncodeError:
            print(json.dumps({"status": "saved_to_file", "file": str(file_path), "review": review}, ensure_ascii=True))


if __name__ == "__main__":
    main()
