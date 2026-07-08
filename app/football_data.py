import asyncio

import httpx

from app.config import settings

# Threshold at which we stop and wait for the counter to reset rather than risk a 429.
_RATE_LIMIT_FLOOR = 1


class FootballDataClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.football_data_base_url,
            headers={"X-Auth-Token": settings.football_data_api_token},
            timeout=10.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        response = await self._client.get(path, params=params or {})
        response.raise_for_status()
        await self._throttle_if_needed(response.headers)
        return response

    async def _throttle_if_needed(self, headers: httpx.Headers) -> None:
        remaining = headers.get("X-RequestsAvailable")
        reset_seconds = headers.get("X-RequestCounter-Reset")
        if remaining is None or reset_seconds is None:
            return

        if int(remaining) <= _RATE_LIMIT_FLOOR:
            await asyncio.sleep(int(reset_seconds) + 1)

    async def get_competition(self, code: str) -> dict:
        response = await self._get(f"/competitions/{code}")
        return response.json()

    async def get_matches(
        self,
        code: str,
        matchday: int | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        params = {}
        if matchday is not None:
            params["matchday"] = matchday
        if status is not None:
            params["status"] = status
        if date_from is not None:
            params["dateFrom"] = date_from
        if date_to is not None:
            params["dateTo"] = date_to

        response = await self._get(f"/competitions/{code}/matches", params=params)
        return response.json()["matches"]
