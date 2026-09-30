"""Send a Telegram message by chat_id using the same Telethon session as telegram-mcp."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User


TELEGRAM_ENV = Path.home() / "telegram-mcp" / ".env"


def _load_env() -> tuple[str, str, str]:
    if not TELEGRAM_ENV.exists():
        raise SystemExit(f"Missing Telegram .env: {TELEGRAM_ENV}")
    load_dotenv(TELEGRAM_ENV, override=True)
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_string = (
        os.getenv("TELEGRAM_SESSION_STRING")
        or os.getenv("TELEGRAM_SESSION_STRING_ARENDA")
        or ""
    )
    if not api_id or not api_hash or not session_string:
        raise SystemExit(
            "TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING must be set in ~/telegram-mcp/.env"
        )
    return api_id, api_hash, session_string


async def send_message(chat_id: str, text: str) -> None:
    api_id, api_hash, session_string = _load_env()
    async with TelegramClient(
        StringSession(session_string),
        int(api_id),
        api_hash,
        flood_sleep_threshold=60,
    ) as client:
        entity = await client.get_entity(chat_id)
        await client.send_message(entity, text)
        if isinstance(entity, User):
            print(f"Sent to {entity.username or entity.first_name or chat_id}")
        else:
            print(f"Sent to {getattr(entity, 'title', chat_id)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a Telegram message by chat_id")
    parser.add_argument("chat_id", help="Telegram chat_id, username or phone number")
    parser.add_argument("message", help="Message text to send")
    args = parser.parse_args()

    try:
        asyncio.run(send_message(args.chat_id, args.message))
    except Exception as exc:
        print(f"Failed to send message: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
