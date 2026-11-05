"""POST /api/chat — one agent turn as Server-Sent Events: status lines while tools run, then the final state."""

import json
import logging
import queue
import threading
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cinesense.core.config import get_settings
from cinesense.core.criteria import SearchCriteria
from cinesense.core.models import Movie
from cinesense.web_api.chat_log import log_turn
from cinesense.web_api.deps import get_agent, get_chat_log, get_limiter, get_provider, get_streaming, log_secret
from cinesense.web_api.images import with_images
from cinesense.web_api.limits import visitor_of
from cinesense.web_api.taste import UserProfile

UNAVAILABLE = "The assistant is unavailable right now — you can still use the chips and search."
IMAGE_FILL = 4
log = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/chat")
def chat(
    req: ChatRequest,
    runner: Annotated[object, Depends(get_agent)],
    provider: Annotated[object, Depends(get_provider)],
    streaming: Annotated[object, Depends(get_streaming)],
    profile: UserProfile,
    request: Request,
    limiter: Annotated[object, Depends(get_limiter)],
    chat_log: Annotated[object, Depends(get_chat_log)],
):
    visitor = visitor_of(request.headers, request.client and request.client.host)
    refused = None if runner is None else limiter.check(visitor)

    def events():
        if runner is None:
            yield _sse("error", {"text": UNAVAILABLE})
            return
        if refused:
            yield _sse("error", {"text": refused})
            return
        q: queue.Queue = queue.Queue()

        def work():
            started, out, error = time.monotonic(), None, None
            try:
                out = runner(
                    req.thread_id, req.message, req.criteria.model_dump(), lambda t: q.put(("status", t)), profile
                )
                for r in out.get("results", [])[:IMAGE_FILL]:
                    r["movie"] = with_images(Movie(**r["movie"]), provider, streaming).model_dump(mode="json")
                u = out.get("usage") or {}
                log.info("chat turn: %s input / %s output tokens", u.get("input_tokens"), u.get("output_tokens"))
                q.put(("final", out))
            except Exception as exc:  # noqa: BLE001 — any LLM/provider failure degrades to the chips
                log.exception("chat turn failed")
                error = type(exc).__name__
                q.put(("error", None))
            log_turn(
                chat_log,
                scope="chat",
                visitor=visitor,
                thread_id=req.thread_id,
                message=req.message,
                out=out,
                duration_s=time.monotonic() - started,
                error=error,
                secret=log_secret(),
                model=get_settings().llm_model,
                tag_names=provider.list_tags(),
            )

        threading.Thread(target=work, daemon=True).start()
        while True:
            kind, payload = q.get()
            if kind == "status":
                yield _sse("status", {"text": payload})
            elif kind == "final":
                keys = ("reply", "criteria", "results", "picks", "proposals", "handoff", "usage", "relaxed")
                yield _sse("final", {k: payload.get(k) for k in keys})
                return
            else:
                yield _sse("error", {"text": UNAVAILABLE})
                return

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
