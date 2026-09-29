from typing import Any, Dict
from ..listing_validator import fetch_page, is_cloudflare_blocked
from ..requirements import validate_requirements, _build_draft_message


def validate(url: str) -> Dict[str, Any]:
    html = fetch_page(url)
    if is_cloudflare_blocked(html):
        return {"status": "blocked_by_cloudflare", "url": url}
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    result = validate_requirements(text)
    missing_must = [item for item in result["missing"] if item["category"] == "must_have"]
    missing_nice = [item for item in result["missing"] if item["category"] == "nice_to_have"]
    present = result["present"]
    prohibited = result["prohibited"]

    passed = len(prohibited) == 0

    if passed and (missing_must or missing_nice):
        draft_message, draft_questions, missing_to_ask = _build_draft_message(missing_must, missing_nice, "halooglasi.com")
    else:
        draft_questions = []
        missing_to_ask = []

    return {
        "status": "ok",
        "site": "halooglasi.com",
        "url": url,
        "must_have_passed": passed,
        "present_items": [f"{m['section']}: {m['item']}" for m in present],
        "missing_must_have": [f"{m['section']}: {m['item']}" for m in missing_must],
        "prohibited_must_have": [f"{m['section']}: {m['item']}" for m in prohibited],
        "raw_listing_text": text,
        "extracted_info": {"text_snippet": text[:1000]},
        "missing_to_ask": missing_to_ask,
        "draft_questions": draft_questions,
        "message_status": "pending_approval" if missing_to_ask else "not_needed",
        "draft_message": draft_message,
        "notes": ["halooglasi parser"],
    }
