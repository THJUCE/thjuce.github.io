from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

import httpx

from api_client import OneDashAPIError, OneDashClient, OneDashRateLimitError


class OneDashClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = OneDashClient(base_url="https://example.com/api", api_key="secret", timeout=5)

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_request_returns_payload(self) -> None:
        response = httpx.Response(200, json={"type": True, "data": {"balance": 100}})
        self.client._client.request = AsyncMock(return_value=response)

        payload = await self.client.balance()

        self.assertEqual(payload["data"]["balance"], 100)

    async def test_request_raises_api_error_on_type_false(self) -> None:
        response = httpx.Response(200, json={"type": False, "err": "wrong_parameters", "message": "Bad"})
        self.client._client.request = AsyncMock(return_value=response)

        with self.assertRaises(OneDashAPIError) as ctx:
            await self.client.balance()

        self.assertEqual(ctx.exception.err, "wrong_parameters")

    async def test_request_raises_rate_limit(self) -> None:
        response = httpx.Response(429, headers={"Retry-After": "9"}, json={"type": False})
        self.client._client.request = AsyncMock(return_value=response)

        with self.assertRaises(OneDashRateLimitError) as ctx:
            await self.client.balance()

        self.assertEqual(ctx.exception.retry_after, 9)

    async def test_create_vps_sends_confirm_and_options(self) -> None:
        response = httpx.Response(200, json={"type": True, "order_id": 100})
        mock = AsyncMock(return_value=response)
        self.client._client.request = mock

        await self.client.create_vps(
            period=30,
            tariff_id=5,
            location="msk",
            processor="intel",
            system="ubuntu_22",
            count=2,
            static_ip=True,
            nvme=False,
            backup=True,
            skip_desktop_link=False,
        )

        _, kwargs = mock.call_args
        self.assertTrue(kwargs["json"]["confirm"])
        self.assertEqual(kwargs["json"]["additional_options"], {"static_ip": True, "nvme": False, "backup": True})


if __name__ == "__main__":
    unittest.main()
