from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    onedash_api_key: str
    admin_user_id: int
    api_base_url: str = "https://api.rdp-onedash.ru/api"
    request_timeout: float = 15.0
    log_file: str = "/var/log/onedash-bot/bot.log"
    log_level: str = "INFO"
    cache_ttl_seconds: int = 60
    debounce_ttl_seconds: int = 4

    @property
    def api_headers(self) -> dict[str, str]:
        return {
            "Authorization": self.onedash_api_key,
            "Api-Key": self.onedash_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }


def load_settings() -> Settings:
    load_dotenv(ENV_PATH)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    onedash_api_key = os.getenv("ONEDASH_API_KEY", "").strip()
    admin_user_id_raw = os.getenv("ADMIN_USER_ID", "").strip()

    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    if not onedash_api_key:
        raise ValueError("ONEDASH_API_KEY is required")
    if not admin_user_id_raw:
        raise ValueError("ADMIN_USER_ID is required")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        onedash_api_key=onedash_api_key,
        admin_user_id=int(admin_user_id_raw),
        api_base_url=os.getenv("ONEDASH_API_BASE_URL", "https://api.rdp-onedash.ru/api").rstrip("/"),
        request_timeout=float(os.getenv("ONEDASH_REQUEST_TIMEOUT", "15")),
        log_file=os.getenv("BOT_LOG_FILE", "/var/log/onedash-bot/bot.log"),
        log_level=os.getenv("BOT_LOG_LEVEL", "INFO").upper(),
        cache_ttl_seconds=int(os.getenv("BOT_CACHE_TTL_SECONDS", "60")),
        debounce_ttl_seconds=int(os.getenv("BOT_DEBOUNCE_TTL_SECONDS", "4")),
    )
