"""Chat model via OpenRouter (OpenAI-compatible API)."""

from langchain_openai import ChatOpenAI

from cinesense.config import Settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


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
