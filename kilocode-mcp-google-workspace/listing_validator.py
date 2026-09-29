from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from requirements import Requirements, validate_requirements, _build_draft_message

WORKSPACE = Path(__file__).resolve().parent.parent


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
    result = validate_requirements(text)
    missing_must = result["missing_must_have"]
    missing_nice = result["missing_nice_to_have"]
    prohibited = result["prohibited"]

    passed = len(prohibited) == 0
    missing_to_ask = []
    draft_message = ""

    if passed and (missing_must or missing_nice):
        draft_message, missing_to_ask = _build_draft_message(missing_must, missing_nice, detect_site(url))

    return {
        "status": "ok",
        "site": detect_site(url),
        "url": url,
        "must_have_passed": passed,
        "missing_must_have": [f"{m['section']}: {m['item']}" for m in missing_must],
        "prohibited_must_have": [f"{m['section']}: {m['item']}" for m in prohibited],
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
