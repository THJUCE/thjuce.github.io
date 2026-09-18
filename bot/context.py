from __future__ import annotations

from dataclasses import dataclass

from api_client import OneDashClient
from config import Settings
from bot.services.cache import TTLCache
from bot.services.guards import OperationGuard


@dataclass(slots=True)
class AppContext:
    settings: Settings
    client: OneDashClient
    cache: TTLCache
    guard: OperationGuard
