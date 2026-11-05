"""Model prices from OpenRouter's public model list (https://openrouter.ai/api/v1/models, no key needed), cached
for six hours. On any failure the caller falls back to its own table."""

import threading
import time

import httpx

MODELS_URL = "https://openrouter.ai/api/v1/models"
TTL_S = 6 * 3600


class PriceList:
    def __init__(self, client: httpx.Client | None = None, clock=time.monotonic) -> None:
        self._client = client
        self._clock = clock
        self._lock = threading.Lock()
        self._prices: dict[str, tuple[float, float]] = {}
        self._at: float | None = None

    def _fetch(self) -> dict[str, tuple[float, float]]:
        client = self._client or httpx.Client(timeout=10)
        r = client.get(MODELS_URL)
        r.raise_for_status()
        out = {}
        for m in r.json().get("data", []):
            p = m.get("pricing") or {}
            try:
                out[m["id"]] = (float(p["prompt"]), float(p["completion"]))
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def prices(self) -> dict[str, tuple[float, float]]:
        """USD per input and output token by model id; {} when OpenRouter cannot be reached."""
        with self._lock:
            if self._at is None or self._clock() - self._at > TTL_S:
                try:
                    self._prices = self._fetch()
                    self._at = self._clock()
                except (httpx.HTTPError, ValueError):
                    return self._prices
            return self._prices
