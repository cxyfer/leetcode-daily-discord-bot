import asyncio
import logging
import random
from urllib.parse import quote

import aiohttp

logger = logging.getLogger("api_client")


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


class ApiProcessingError(Exception):
    def __init__(self, detail: str = "Resource is being processed"):
        self.detail = detail
        super().__init__(detail)


class ApiNetworkError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ApiRateLimitError(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")


class OjApiClient:
    def __init__(self, base_url: str, token: str | None = None, timeout: int = 10):
        self._base_url = base_url.rstrip("/")
        self._token = token if token else None
        self._timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._inflight: dict[str, asyncio.Future] = {}

    async def start(self):
        if self._session and not self._session.closed:
            return
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10, keepalive_timeout=30)
        base_url = self._base_url.rstrip("/") + "/"
        self._session = aiohttp.ClientSession(
            base_url=base_url,
            headers=headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        )
        logger.info("API client session started (base_url=%s)", self._base_url)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("API client session closed")

    # -- HTTP layer --

    async def _do_request(self, method: str, path: str, **kwargs) -> dict | None:
        assert self._session, "Call start() before making requests"
        try:
            async with self._session.request(method, path, **kwargs) as resp:
                status = resp.status
                if status == 200:
                    return await resp.json()
                if status == 404:
                    return None
                if status == 202:
                    detail = await self._parse_detail(resp)
                    raise ApiProcessingError(detail)
                if status == 429:
                    retry_after = float(resp.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    async with self._session.request(method, path, **kwargs) as retry_resp:
                        if retry_resp.status == 200:
                            return await retry_resp.json()
                        if retry_resp.status == 404:
                            return None
                        if retry_resp.status == 429:
                            ra = float(retry_resp.headers.get("Retry-After", 5))
                            raise ApiRateLimitError(ra)
                        detail = await self._parse_detail(retry_resp)
                        raise ApiError(retry_resp.status, detail)
                detail = await self._parse_detail(resp)
                raise ApiError(status, detail)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            raise ApiNetworkError(str(e)) from e

    @staticmethod
    async def _parse_detail(resp: aiohttp.ClientResponse) -> str:
        try:
            body = await resp.json()
            return body.get("detail", body.get("title", str(body)))
        except Exception:
            return "Invalid response body"

    async def _request(self, method: str, path: str, **kwargs) -> dict | None:
        params = kwargs.get("params")
        key = f"{method}:{path}"
        if params:
            sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
            key = f"{key}?{sorted_params}"

        if key in self._inflight:
            return await self._inflight[key]

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._inflight[key] = future
        try:
            result = await self._do_request(method, path, **kwargs)
            future.set_result(result)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            self._inflight.pop(key, None)

    # -- Public API --

    async def get_problem(self, source: str, id: str) -> dict | None:
        return await self._request("GET", f"problems/{quote(source)}/{quote(id)}")

    async def get_daily(self, domain: str = "com", date: str | None = None) -> dict | None:
        params = {"domain": domain}
        if date:
            params["date"] = date
        return await self._request("GET", "daily", params=params)

    async def resolve(self, query: str) -> dict | None:
        return await self._request("GET", f"resolve/{quote(query, safe='')}")

    async def search_similar_by_id(
        self, source: str, id: str, top_k: int = 5, min_similarity: float = 0.7
    ) -> dict | None:
        params = {"limit": str(top_k), "threshold": str(min_similarity)}
        return await self._request("GET", f"similar/{quote(source)}/{quote(id)}", params=params)

    async def search_similar_by_text(
        self, query: str, source: str | None = None, top_k: int = 5, min_similarity: float = 0.7
    ) -> dict | None:
        params: dict[str, str] = {"q": query, "limit": str(top_k), "threshold": str(min_similarity)}
        if source:
            params["source"] = source
        return await self._request("GET", "similar", params=params)

    @staticmethod
    def _list_total(response: dict) -> int:
        total = response.get("total")
        if total is None:
            total = (response.get("meta") or {}).get("total")
        return int(total or 0)

    @staticmethod
    def _list_items(response: dict) -> list:
        for key in ("results", "items", "data"):
            items = response.get(key)
            if isinstance(items, list):
                return items
        return []

    async def get_random_problem(
        self,
        *,
        difficulty: str | None = None,
        tags: str | None = None,
        rating_min: int | None = None,
        rating_max: int | None = None,
    ) -> dict | None:
        """Fetch a random LeetCode problem via two-call strategy.

        Returns the problem dict on success, None if no problems match,
        or propagates standard API errors.
        """
        if rating_min is not None and rating_max is not None and rating_min > rating_max:
            rating_min, rating_max = rating_max, rating_min

        base_params: dict[str, str | int] = {"per_page": 1}
        if difficulty:
            base_params["difficulty"] = difficulty
        if tags:
            base_params["tags"] = tags
        if rating_min is not None:
            base_params["rating_min"] = rating_min
        if rating_max is not None:
            base_params["rating_max"] = rating_max

        count_resp = await self._request("GET", "problems/leetcode", params=base_params)
        if not count_resp:
            return None

        total = self._list_total(count_resp)
        if total == 0:
            return None

        random_page = random.randint(1, total)
        page_params = {**base_params, "page": random_page}
        result = await self._request("GET", "problems/leetcode", params=page_params)
        if not result:
            return None

        items = self._list_items(result)
        if not items:
            # TOCTOU fallback: dataset shrank between count and fetch
            page_params["page"] = 1
            result = await self._request("GET", "problems/leetcode", params=page_params)
            if not result:
                return None
            items = self._list_items(result)

        return items[0] if items else None
