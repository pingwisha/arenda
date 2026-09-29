import os
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent


def load_env() -> None:
    env_path = WORKSPACE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_credentials() -> tuple[str, str]:
    load_env()
    login = os.environ.get("HALO_LOGIN", "")
    password = os.environ.get("HALO_PASS", "")
    if not login or not password:
        raise RuntimeError("HALO_LOGIN or HALO_PASS not set in .env")
    return login, password


def send_message(listing_url: str, message_text: str) -> dict:
    login, password = get_credentials()
    print(f"Prepared credentials for user: {login}")
    print(f"Message preview: {message_text}")

    chrome_url = "http://127.0.0.1:9222"
    return {
        "status": "awaiting_send",
        "listing_url": listing_url,
        "message": message_text,
        "credentials_user": login,
        "chrome_url": chrome_url,
        "instructions": "User must confirm sending. After confirmation, run chrome-devtools-axi against the existing Chrome session on port 9222 to fill and submit the contact form. Do not expose password.",
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python listing_sender.py <listing_url> <message_text>")
        return 1

    listing_url = sys.argv[1]
    message_text = sys.argv[2]
    result = send_message(listing_url, message_text)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
