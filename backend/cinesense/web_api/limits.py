"""Chat limits: every agent turn (chat and /api/inspect) costs real LLM money, so turns are capped per visitor
(per minute and per day) and for the whole site per day; the technical view has its own counter (deps.py).

The daily counts live in a store: Postgres in production (table `chat_turns`), so a restart of the API does not
hand out a fresh quota; in memory without a database. Postgres keeps only today's rows and stores a keyed hash
of the visitor's address, never the address itself. The per-minute window stays in memory (a restart takes
longer than the window). If the store fails, the limiter counts in memory instead of blocking the chat.
Refused turns are not counted."""

import datetime as dt
import hashlib
import hmac
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping

log = logging.getLogger(__name__)

VISITOR_MINUTE = "One moment please: that was a lot of questions in a minute. Try again shortly."
VISITOR_DAY = "You've reached today's limit for the assistant. The chips and the search still work."
SITE_DAY = "The assistant has reached its limit for today. The chips and the search still work."

SITE = "*"  # the row that counts every visitor of a scope together


class MemoryTurnStore:
    """Daily turn counts in the process (tests, local development without a database)."""

    def __init__(self) -> None:
        self._counts: dict[tuple[dt.date, str, str], int] = defaultdict(int)

    def counts(self, day: dt.date, scope: str, visitor: str) -> tuple[int, int]:
        return self._counts.get((day, scope, visitor), 0), self._counts.get((day, scope, SITE), 0)

    def add(self, day: dt.date, scope: str, visitor: str) -> None:
        for key in [k for k in self._counts if k[0] < day]:
            del self._counts[key]
        self._counts[(day, scope, visitor)] += 1
        self._counts[(day, scope, SITE)] += 1


class PostgresTurnStore:
    """Daily turn counts in `chat_turns` (database/schema.sql): one row per day, scope and hashed visitor, plus
    the site row. Each count drops the rows of earlier days."""

    DDL = (
        "create table if not exists chat_turns (day date not null, scope text not null, visitor text not null, "
        "turns int not null default 0, primary key (day, scope, visitor))"
    )

    def __init__(self, conn_factory, secret: str) -> None:
        self._conn = conn_factory
        self._key = secret.encode()
        self._ready = False

    def _ensure_table(self, c) -> None:
        """The live database gets the table on first use (deploys ship the code, not database/schema.sql)."""
        if not self._ready:
            c.execute(self.DDL)
            c.commit()
            self._ready = True

    def _visitor(self, visitor: str) -> str:
        return hmac.new(self._key, visitor.encode(), hashlib.sha256).hexdigest()[:32]

    def counts(self, day: dt.date, scope: str, visitor: str) -> tuple[int, int]:
        hashed = self._visitor(visitor)
        with self._conn() as c:
            self._ensure_table(c)
            rows = c.execute(
                "select visitor, turns from chat_turns where day = %s and scope = %s and visitor in (%s, %s)",
                (day, scope, hashed, SITE),
            ).fetchall()
        found = {r[0]: int(r[1]) for r in rows}
        return found.get(hashed, 0), found.get(SITE, 0)

    def add(self, day: dt.date, scope: str, visitor: str) -> None:
        with self._conn() as c:
            self._ensure_table(c)
            c.execute("delete from chat_turns where day < %s", (day,))
            for who in (self._visitor(visitor), SITE):
                c.execute(
                    "insert into chat_turns (day, scope, visitor, turns) values (%s, %s, %s, 1) "
                    "on conflict (day, scope, visitor) do update set turns = chat_turns.turns + 1",
                    (day, scope, who),
                )
            c.commit()


class TurnLimiter:
    def __init__(
        self,
        per_visitor_minute: int,
        per_visitor_day: int,
        site_day: int,
        clock: Callable[[], float] = time.time,
        store=None,
        scope: str = "chat",
    ):
        self.per_visitor_minute = per_visitor_minute
        self.per_visitor_day = per_visitor_day
        self.site_day = site_day
        self.clock = clock
        self.scope = scope
        self.store = store if store is not None else MemoryTurnStore()
        self._fallback = MemoryTurnStore()
        self._lock = threading.Lock()
        self._day: dt.date | None = None
        self._recent: dict[str, deque[float]] = defaultdict(deque)

    def _counts(self, day: dt.date, visitor: str) -> tuple[int, int]:
        try:
            return self.store.counts(day, self.scope, visitor)
        except Exception:
            log.exception("chat limit store failed; counting in memory")
            return self._fallback.counts(day, self.scope, visitor)

    def _add(self, day: dt.date, visitor: str) -> None:
        try:
            self.store.add(day, self.scope, visitor)
        except Exception:
            log.exception("chat limit store failed; counting in memory")
            self._fallback.add(day, self.scope, visitor)

    def check(self, visitor: str) -> str | None:
        """None if the turn may run (and counts it), otherwise the message to show instead."""
        with self._lock:
            now = self.clock()
            day = dt.datetime.fromtimestamp(now, dt.UTC).date()
            if day != self._day:
                self._day = day
                self._recent.clear()
            recent = self._recent[visitor]
            while recent and recent[0] <= now - 60:
                recent.popleft()
            mine, site = self._counts(day, visitor)
            if site >= self.site_day:
                return SITE_DAY
            if mine >= self.per_visitor_day:
                return VISITOR_DAY
            if len(recent) >= self.per_visitor_minute:
                return VISITOR_MINUTE
            recent.append(now)
            self._add(day, visitor)
            return None


def visitor_of(headers: Mapping[str, str], client_host: str | None) -> str:
    """The client address: the last X-Forwarded-For entry (added by our own proxy, Caddy or nginx), else the
    direct peer. Earlier entries come from the client and could be forged."""
    forwarded = headers.get("x-forwarded-for", "")
    last = forwarded.rsplit(",", 1)[-1].strip()
    return last or client_host or "unknown"
