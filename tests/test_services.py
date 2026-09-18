from __future__ import annotations

import asyncio
import unittest

from bot.formatters import days_until, extract_price_for_period, humanize_os_name
from bot.services.cache import TTLCache
from bot.services.guards import BusyOperationError, OperationGuard


class FormatterTests(unittest.TestCase):
    def test_extract_price_for_period(self) -> None:
        tariff = {"prices": [{"period": 7, "price": 10}, {"period": 30, "price": 20}]}
        self.assertEqual(extract_price_for_period(tariff, 30)["price"], 20)

    def test_humanize_os_name_falls_back_to_code(self) -> None:
        systems = [{"code": "ubuntu_22", "name": "Ubuntu 22"}]
        self.assertEqual(humanize_os_name("unknown", systems), "unknown")

    def test_days_until_none(self) -> None:
        self.assertIsNone(days_until(None))


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_ttl_cache_expires(self) -> None:
        cache = TTLCache(ttl_seconds=1)
        await cache.set("k", "v", ttl_seconds=0)
        self.assertIsNone(await cache.get("k"))


class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_guard_blocks_duplicate_operation(self) -> None:
        guard = OperationGuard(cooldown_seconds=1)
        async with guard.lock("job"):
            with self.assertRaises(BusyOperationError):
                async with guard.lock("job"):
                    pass
        with self.assertRaises(BusyOperationError):
            async with guard.lock("job"):
                pass
        await asyncio.sleep(1.1)
        async with guard.lock("job"):
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
