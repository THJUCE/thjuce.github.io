from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OneDashAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, err: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.err = err


class OneDashRateLimitError(OneDashAPIError):
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, status_code=429, err="rate_limited")
        self.retry_after = retry_after


class OneDashClient:
    def __init__(self, *, base_url: str, api_key: str, timeout: float = 15.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": api_key,
                "Api-Key": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        allow_202: bool = True,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise OneDashAPIError("OneDash API did not respond in time") from exc
        except httpx.HTTPError as exc:
            raise OneDashAPIError("Failed to connect to OneDash API") from exc

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise OneDashRateLimitError(
                "OneDash API rate limit exceeded",
                retry_after=int(retry_after) if retry_after and retry_after.isdigit() else None,
            )

        if response.status_code not in {200, 202 if allow_202 else 200}:
            details = self._extract_error(response)
            raise OneDashAPIError(details["message"], status_code=response.status_code, err=details.get("err"))

        payload = response.json()
        if not isinstance(payload, dict):
            raise OneDashAPIError("OneDash API returned an invalid response")
        if payload.get("type") is False:
            raise OneDashAPIError(
                payload.get("message") or "OneDash API returned an error",
                status_code=response.status_code,
                err=payload.get("err"),
            )
        return payload

    @staticmethod
    def _extract_error(response: httpx.Response) -> dict[str, str | None]:
        try:
            payload = response.json()
        except ValueError:
            return {"message": f"HTTP {response.status_code} from OneDash API", "err": None}
        if isinstance(payload, dict):
            return {
                "message": payload.get("message") or f"HTTP {response.status_code} from OneDash API",
                "err": payload.get("err"),
            }
        return {"message": f"HTTP {response.status_code} from OneDash API", "err": None}

    async def ping(self) -> dict[str, Any]:
        return await self._request("GET", "/ping")

    async def auth_check(self) -> dict[str, Any]:
        return await self._request("GET", "/auth/check")

    async def locations(self) -> dict[str, Any]:
        return await self._request("GET", "/locations")

    async def systems(self) -> dict[str, Any]:
        return await self._request("GET", "/systems")

    async def tariffs(self, *, location: str, processor: str) -> dict[str, Any]:
        return await self._request("GET", "/tariffs", params={"location": location, "processor": processor})

    async def balance(self) -> dict[str, Any]:
        return await self._request("GET", "/balance")

    async def top_up_balance(self, amount: int | float) -> dict[str, Any]:
        return await self._request("POST", "/balance/top-up", json={"amount": amount})

    async def orders(self) -> dict[str, Any]:
        return await self._request("GET", "/orders")

    async def order_info(self, *, order_id: int) -> dict[str, Any]:
        return await self._request("POST", "/orders/info", json={"order_id": order_id})

    async def renew_order(self, *, order_id: int, period: int) -> dict[str, Any]:
        return await self._request("POST", "/orders/renew", json={"order_id": order_id, "period": period, "confirm": True})

    async def change_order_tariff(self, *, order_id: int, tariff_id: int) -> dict[str, Any]:
        return await self._request("POST", f"/orders/{order_id}/tariff", json={"tariff_id": tariff_id, "confirm": True})

    async def vps_list(self, *, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        return await self._request("GET", "/vps", params={"page": page, "per_page": per_page})

    async def create_vps(
        self,
        *,
        period: int,
        tariff_id: int,
        location: str,
        processor: str,
        system: str,
        count: int,
        static_ip: bool,
        nvme: bool,
        backup: bool,
        skip_desktop_link: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "period": period,
            "tariff_id": tariff_id,
            "location": location,
            "processor": processor,
            "system": system,
            "count": count,
            "skip_desktop_link": skip_desktop_link,
            "additional_options": {
                "static_ip": static_ip,
                "nvme": nvme,
                "backup": backup,
            },
            "confirm": True,
        }
        return await self._request("POST", "/vps/create", json=payload)

    async def clone_vps(self, *, source_vps_id: int, target_vpses: list[int]) -> dict[str, Any]:
        payload = {"source_vps_id": source_vps_id, "target_vpses": target_vpses, "confirm": True}
        return await self._request("POST", "/vps/clone", json=payload)

    async def vps_credentials(self, *, vps_id: int) -> dict[str, Any]:
        return await self._request("POST", f"/vps/{vps_id}/credentials", json={})

    async def power_status(self, *, vps_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/vps/{vps_id}/power")

    async def power_action(self, *, vps_id: int, action: str) -> dict[str, Any]:
        return await self._request("POST", f"/vps/{vps_id}/power", json={"action": action})

    async def reinstall_vps(self, *, vps_id: int, system: str) -> dict[str, Any]:
        return await self._request("POST", f"/vps/{vps_id}/reinstall", json={"system": system, "confirm": True})
