"""OpenRouter embeddings (openai/text-embedding-3-small, 1,536 dims)."""

import asyncio

import httpx

EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
DEFAULT_MODEL = "openai/text-embedding-3-small"
DIMENSIONS = 1536


class EmbeddingClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        http: httpx.AsyncClient | None = None,
        batch: int = 100,
    ):
        self.api_key = api_key
        self.model = model
        self.http = http
        self.batch = batch
        self.total_tokens = 0
        self.total_cost = 0.0

    async def _post(self, http: httpx.AsyncClient, texts: list[str], retries: int = 4) -> list[list[float]]:
        for attempt in range(retries):
            r = await http.post(
                EMBEDDINGS_URL,
                json={"model": self.model, "input": texts},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60,
            )
            if r.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(2**attempt * 2)
                continue
            r.raise_for_status()
            body = r.json()
            usage = body.get("usage") or {}
            self.total_tokens += int(usage.get("total_tokens") or 0)
            self.total_cost += float(usage.get("cost") or 0.0)
            return [d["embedding"] for d in sorted(body["data"], key=lambda d: d["index"])]
        r.raise_for_status()
        return []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self.http is not None:
            return await self._embed_with(self.http, texts)
        async with httpx.AsyncClient() as http:
            return await self._embed_with(http, texts)

    async def _embed_with(self, http: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            out.extend(await self._post(http, texts[i : i + self.batch]))
        return out
