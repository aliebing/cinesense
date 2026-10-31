"""Chat model via OpenRouter (OpenAI-compatible API)."""

from langchain_openai import ChatOpenAI

from cinesense.config import Settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# USD per token, from https://openrouter.ai/api/v1/models (checked 2026-10-29)
PRICES = {
    "anthropic/claude-haiku-5.5": (0.10e-6, 0.50e-6),
    "anthropic/claude-sonnet-5.5": (2.0e-6, 10.0e-6),
}


def cost_usd(usage: dict, price: tuple[float, float]) -> float:
    return round(usage.get("input_tokens", 0) * price[0] + usage.get("output_tokens", 0) * price[1], 6)


def make_llm(settings: Settings, *, max_tokens: int = 700, timeout: int = 45) -> ChatOpenAI | None:
    if not settings.openrouter_api_key:
        return None
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url=OPENROUTER_BASE,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=1,
        temperature=0.3,
        default_headers={"HTTP-Referer": "https://github.com/aliebing", "X-Title": "CineSense"},
    )
