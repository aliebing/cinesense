"""POST /api/inspect — one agent turn with everything behind it, as plain JSON for the technical review page
(/tech): the reply, the criteria with tag names, the ranked films as text, every tool call with its arguments and
result, the prompts that were sent, model, tokens, cost and latency. No images are looked up (no Streaming budget)."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from cinesense.agent.graph import criteria_summary
from cinesense.agent.llm import PRICES, cost_usd
from cinesense.api.chat import ChatRequest
from cinesense.api.deps import get_agent, get_provider
from cinesense.config import get_settings

router = APIRouter()


def _film(r: dict) -> dict:
    m = r["movie"]
    return {
        "id": m["id"],
        "imdb_id": m.get("imdb_id"),
        "title": m["title"],
        "year": m.get("year"),
        "match_percent": r.get("match_percent"),
        "score": r.get("score"),
        "reasons": r.get("reasons", []),
        "genres": m.get("genres", []),
        "worlds": m.get("world_ids", []),
        "directors": m.get("directors", []),
        "cast": m.get("cast_top", []),
        "runtime_min": m.get("runtime_min"),
        "ml_rating": m.get("ml_rating"),
        "ml_rating_count": m.get("ml_rating_count"),
        "overview": m.get("overview"),
    }


@router.post("/api/inspect")
def inspect(
    req: ChatRequest,
    runner: Annotated[object, Depends(get_agent)],
    provider: Annotated[object, Depends(get_provider)],
) -> dict:
    if runner is None:
        raise HTTPException(status_code=503, detail="no_llm_key")
    started = time.monotonic()
    out = runner(req.thread_id, req.message, req.criteria.model_dump(), None, None)
    latency = time.monotonic() - started
    names = provider.list_tags()
    criteria = out.get("criteria") or {}
    model = get_settings().llm_model
    usage = out.get("usage") or {}
    return {
        "reply": out.get("reply", ""),
        "picks": out.get("picks", 0),
        "results": [_film(r) for r in out.get("results", [])],
        "criteria": criteria,
        "criteria_summary": criteria_summary(criteria, names),
        "tags": [
            {
                "tag": names[t["idx"]] if t["idx"] < len(names) else f"#{t['idx']}",
                "weight": t["weight"],
                "mode": t["mode"],
            }
            for t in criteria.get("tags", [])
        ],
        "proposals": out.get("proposals", []),
        "tools": out.get("tool_trace", []),
        "prompts": out.get("prompts", {}),
        "model": model,
        "usage": usage,
        "cost_usd": cost_usd(usage, PRICES.get(model, (0.0, 0.0))),  # unknown model: shown as 0
        "latency_s": round(latency, 2),
        "rounds": out.get("rounds", 0),
        "grounding_fallback": out.get("grounding_fallback", False),
        "grounding_reason": out.get("grounding_reason", []),
    }
