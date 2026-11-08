"""GET /api/admin/visitors[/{id}]: the visitor log (chat_log.py) for the login-protected /admin/visitors page —
the latest turns with sums, and one turn in full with the earlier messages of its conversation."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from cinesense.web_api.admin_session import require_tech_login
from cinesense.web_api.deps import get_chat_log

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_tech_login)])


@router.get("/visitors")
def visitors(
    chat_log: Annotated[object, Depends(get_chat_log)],
    scope: Literal["chat", "tech"] | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    return chat_log.page(scope, offset, limit)


@router.get("/visitors/{entry_id}")
def visitor_turn(entry_id: int, chat_log: Annotated[object, Depends(get_chat_log)]) -> dict:
    found = chat_log.detail(entry_id)
    if found is None:
        raise HTTPException(status_code=404, detail="unknown turn")
    return found
