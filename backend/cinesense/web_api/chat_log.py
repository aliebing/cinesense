"""Visitor log: one entry per agent turn (chat and /api/inspect) for the login-protected /admin/visitors page.

Kept for `chat_log_days` (30, as the privacy notice says): every write drops older entries. Stores the message,
the reply, the understood criteria, the films shown, the tool calls, tokens, cost and duration, and two keyed
hashes: of the visitor's address (never the address itself) and of the conversation id, so the turns of one
conversation can be shown together. Writing never breaks a turn: a failing store is logged and skipped."""

import datetime as dt
import hashlib
import hmac
import json
import logging
import threading

log = logging.getLogger(__name__)

FIELDS = (
    "ts",
    "scope",
    "visitor",
    "thread",
    "message",
    "reply",
    "criteria",
    "criteria_summary",
    "films",
    "tools",
    "relaxed",
    "grounding_fallback",
    "grounding_reason",
    "guarded",
    "model",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "duration_ms",
    "error",
)
JSON_FIELDS = {"criteria", "films", "tools", "relaxed", "grounding_reason"}
SUMMARY = ("id", "ts", "scope", "visitor", "thread", "message", "films", "tools", "grounding_fallback", "guarded")
SUMMARY += ("input_tokens", "output_tokens", "cost_usd", "duration_ms", "error")


def keyed_hash(secret: str, value: str, length: int = 12) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:length]


def entry_from_turn(out: dict | None, **fields) -> dict:
    """The log entry for one finished (or failed: out=None) turn. `fields` are scope, visitor, thread, message,
    model, cost_usd, duration_ms, error and criteria_summary, already prepared by the caller."""
    out = out or {}
    usage = out.get("usage") or {}
    films = [
        {"title": r["movie"]["title"], "year": r["movie"].get("year"), "match": r.get("match_percent")}
        for r in (out.get("results") or [])[:10]
    ]
    tools = [{"name": t["name"], "args": t.get("args", {})} for t in out.get("tool_trace") or []]
    return {
        "ts": dt.datetime.now(dt.UTC),
        "reply": out.get("reply"),
        "criteria": out.get("criteria"),
        "films": films,
        "tools": tools,
        "relaxed": out.get("relaxed") or [],
        "grounding_fallback": bool(out.get("grounding_fallback")),
        "grounding_reason": out.get("grounding_reason") or [],
        "guarded": bool(out.get("guarded")),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        **fields,
    }


def _summary(e: dict) -> dict:
    s = {k: e.get(k) for k in SUMMARY}
    s["films"] = len(e.get("films") or [])
    s["tools"] = [t["name"] for t in e.get("tools") or []]
    return s


def _sums(entries: list[dict]) -> dict:
    n = len(entries)
    return {
        "count": n,
        "cost_usd": round(sum(e.get("cost_usd") or 0 for e in entries), 4),
        "avg_duration_ms": round(sum(e.get("duration_ms") or 0 for e in entries) / n) if n else None,
        "visitors": len({e.get("visitor") for e in entries if e.get("scope") == "chat"}),
    }


class MemoryChatLog:
    """In the process (tests, local development without a database)."""

    def __init__(self, days: int = 30) -> None:
        self.days = days
        self._entries: list[dict] = []
        self._lock = threading.Lock()

    def write(self, entry: dict) -> None:
        with self._lock:
            cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=self.days)
            self._entries = [e for e in self._entries if e["ts"] > cutoff]
            self._entries.append({**entry, "id": (self._entries[-1]["id"] + 1) if self._entries else 1})

    def _scoped(self, scope: str | None) -> list[dict]:
        return [e for e in reversed(self._entries) if scope is None or e["scope"] == scope]

    def page(self, scope: str | None, offset: int, limit: int) -> dict:
        entries = self._scoped(scope)
        return {"items": [_summary(e) for e in entries[offset : offset + limit]], "total": len(entries)} | {
            "sums": _sums(entries)
        }

    def detail(self, entry_id: int) -> dict | None:
        found = next((e for e in self._entries if e["id"] == entry_id), None)
        if found is None:
            return None
        earlier = [e for e in self._entries if e["thread"] == found["thread"] and e["id"] < entry_id]
        return {**found, "conversation": [{"id": e["id"], "ts": e["ts"], "message": e["message"]} for e in earlier]}


class PostgresChatLog:
    """Table `chat_log` (database/schema.sql), created on first use like `chat_turns`."""

    DDL = """create table if not exists chat_log (
      id bigserial primary key,
      ts timestamptz not null default now(),
      scope text not null,
      visitor text,
      thread text,
      message text,
      reply text,
      criteria jsonb,
      criteria_summary text,
      films jsonb,
      tools jsonb,
      relaxed jsonb,
      grounding_fallback boolean not null default false,
      grounding_reason jsonb,
      guarded boolean not null default false,
      model text,
      input_tokens int not null default 0,
      output_tokens int not null default 0,
      cost_usd double precision not null default 0,
      duration_ms int,
      error text
    );
    create index if not exists chat_log_ts on chat_log (ts desc)"""

    def __init__(self, conn_factory, days: int = 30) -> None:
        self._conn = conn_factory
        self.days = days
        self._ready = False

    def _ensure_table(self, c) -> None:
        if not self._ready:
            for statement in self.DDL.split(";"):
                c.execute(statement)
            c.commit()
            self._ready = True

    def write(self, entry: dict) -> None:
        values = [json.dumps(entry.get(k)) if k in JSON_FIELDS else entry.get(k) for k in FIELDS]
        with self._conn() as c:
            self._ensure_table(c)
            c.execute("delete from chat_log where ts < now() - make_interval(days => %s)", (self.days,))
            c.execute(f"insert into chat_log ({', '.join(FIELDS)}) values ({', '.join(['%s'] * len(FIELDS))})", values)
            c.commit()

    def _rows(self, c, sql: str, args: tuple) -> list[dict]:
        cur = c.execute(sql, args)
        names = [d.name for d in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]

    def page(self, scope: str | None, offset: int, limit: int) -> dict:
        where, args = ("where scope = %s", (scope,)) if scope else ("", ())
        cols = ", ".join(c for c in SUMMARY if c not in ("films", "tools")) + ", films, tools"
        with self._conn() as c:
            self._ensure_table(c)
            items = self._rows(
                c, f"select {cols} from chat_log {where} order by id desc offset %s limit %s", (*args, offset, limit)
            )
            total, cost, avg, visitors = c.execute(
                f"select count(*), coalesce(sum(cost_usd), 0), avg(duration_ms), "
                f"count(distinct visitor) filter (where scope = 'chat') from chat_log {where}",
                args,
            ).fetchone()
        return {
            "items": [_summary(e) for e in items],
            "total": total,
            "sums": {
                "count": total,
                "cost_usd": round(float(cost), 4),
                "avg_duration_ms": round(float(avg)) if avg is not None else None,
                "visitors": visitors,
            },
        }

    def detail(self, entry_id: int) -> dict | None:
        with self._conn() as c:
            self._ensure_table(c)
            rows = self._rows(c, "select * from chat_log where id = %s", (entry_id,))
            if not rows:
                return None
            found = rows[0]
            earlier = self._rows(
                c,
                "select id, ts, message from chat_log where thread = %s and id < %s order by id",
                (found["thread"], entry_id),
            )
        return {**found, "conversation": earlier}


def log_turn(
    store,
    *,
    scope: str,
    visitor: str,
    thread_id: str,
    message: str,
    out: dict | None,
    duration_s: float,
    error: str | None,
    secret: str,
    model: str,
    tag_names: list[str],
) -> None:
    """Prepares and writes the entry of one turn (chat.py, inspect.py). Never raises."""
    if store is None:
        return
    try:
        from cinesense.chat_agent.graph import criteria_summary
        from cinesense.chat_agent.llm import PRICES, cost_usd

        usage = (out or {}).get("usage") or {}
        entry = entry_from_turn(
            out,
            scope=scope,
            visitor=keyed_hash(secret, visitor),
            thread=keyed_hash(secret, thread_id),
            message=message,
            model=model,
            cost_usd=cost_usd(usage, PRICES.get(model, (0.0, 0.0))),
            duration_ms=round(duration_s * 1000),
            error=error,
            criteria_summary=criteria_summary((out or {}).get("criteria") or {}, tag_names) if out else None,
        )
    except Exception:  # noqa: BLE001
        log.exception("visitor log entry failed")
        return
    record(store, entry)


def record(store, entry: dict) -> None:
    """Writes one entry; a failing store never breaks the turn."""
    if store is None:
        return
    try:
        store.write(entry)
    except Exception:  # noqa: BLE001
        log.exception("visitor log write failed")
