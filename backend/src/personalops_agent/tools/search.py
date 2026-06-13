from __future__ import annotations

import httpx

from personalops_agent.config import Settings
from personalops_agent.tools.models import SearchItem, SearchResult


class SearchTool:
    """Zhipu web search wrapper."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def search_web(
        self,
        query: str,
        locale: str = "zh-CN",
        max_results: int = 5,
        post=None,
        client_factory=httpx.AsyncClient,
    ) -> SearchResult:
        if not self.settings.zhipu_api_key:
            return SearchResult(
                ok=False,
                error="ZHIPU_API_KEY is required for real web search; no fake results returned.",
            )

        url = self.settings.zhipu_web_search_url()
        payload = {
            "search_engine": "search_std",
            "search_query": query,
            "count": max_results,
        }
        headers = {"Authorization": f"Bearer {self.settings.zhipu_api_key}"}
        if post is None:
            async with client_factory(timeout=20) as client:
                response = await client.post(url, headers=headers, json=payload)
        else:
            response = await post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        items = [
            SearchItem(
                title=item.get("title", ""),
                url=item.get("link", "") or item.get("url", ""),
                snippet=item.get("content", "")
                or item.get("snippet", "")
                or item.get("summary", ""),
            )
            for item in data.get("search_result", [])
        ]
        return SearchResult(ok=True, items=items)
