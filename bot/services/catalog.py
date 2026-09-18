from __future__ import annotations

from typing import Any

from bot.context import AppContext


async def get_locations(app_context: AppContext) -> list[dict[str, Any]]:
    cache_key = "locations"
    cached = await app_context.cache.get(cache_key)
    if cached is not None:
        return cached
    data = (await app_context.client.locations()).get("data", {})
    locations = data.get("locations", [])
    await app_context.cache.set(cache_key, locations)
    return locations


async def get_systems(app_context: AppContext) -> list[dict[str, Any]]:
    cache_key = "systems"
    cached = await app_context.cache.get(cache_key)
    if cached is not None:
        return cached
    systems = (await app_context.client.systems()).get("data", [])
    await app_context.cache.set(cache_key, systems)
    return systems


async def get_tariffs(app_context: AppContext, *, location: str, processor: str) -> dict[str, Any]:
    cache_key = f"tariffs:{location}:{processor}"
    cached = await app_context.cache.get(cache_key)
    if cached is not None:
        return cached
    data = (await app_context.client.tariffs(location=location, processor=processor)).get("data", {})
    await app_context.cache.set(cache_key, data)
    return data


async def get_vps_items(app_context: AppContext, *, force: bool = False) -> list[dict[str, Any]]:
    cache_key = "vps:list"
    if not force:
        cached = await app_context.cache.get(cache_key)
        if cached is not None:
            return cached
    data = (await app_context.client.vps_list()).get("data", {})
    items = data.get("items", [])
    await app_context.cache.set(cache_key, items, ttl_seconds=20)
    return items
