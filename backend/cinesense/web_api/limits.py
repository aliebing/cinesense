"""Chat limits: every agent turn (chat and /api/inspect) costs real LLM money, so turns are capped per visitor
(per minute and per day) and for the whole site per day. Counted in memory: one API process, and a restart only
ever resets the counters to zero. Refused turns are not counted."""

import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping

VISITOR_MINUTE = "One moment please: that was a lot of questions in a minute. Try again shortly."
VISITOR_DAY = "You've reached today's limit for the assistant. The chips and the search still work."
SITE_DAY = "The assistant has reached its limit for today. The chips and the search still work."


class TurnLimiter:
    def __init__(
        self,
        per_visitor_minute: int,
        per_visitor_day: int,
        site_day: int,
        clock: Callable[[], float] = time.time,
    ):
        self.per_visitor_minute = per_visitor_minute
        self.per_visitor_day = per_visitor_day
        self.site_day = site_day
        self.clock = clock
        self._day = None
        self._site = 0
        self._daily: dict[str, int] = defaultdict(int)
        self._recent: dict[str, deque[float]] = defaultdict(deque)

    def check(self, visitor: str) -> str | None:
        """None if the turn may run (and counts it), otherwise the message to show instead."""
        now = self.clock()
        day = int(now // 86_400)  # UTC day
        if day != self._day:
            self._day, self._site = day, 0
            self._daily.clear()
            self._recent.clear()
        recent = self._recent[visitor]
        while recent and recent[0] <= now - 60:
            recent.popleft()
        if self._site >= self.site_day:
            return SITE_DAY
        if self._daily[visitor] >= self.per_visitor_day:
            return VISITOR_DAY
        if len(recent) >= self.per_visitor_minute:
            return VISITOR_MINUTE
        recent.append(now)
        self._daily[visitor] += 1
        self._site += 1
        return None


def visitor_of(headers: Mapping[str, str], client_host: str | None) -> str:
    """The client address: the last X-Forwarded-For entry (added by our own proxy, Caddy or nginx), else the
    direct peer. Earlier entries come from the client and could be forged."""
    forwarded = headers.get("x-forwarded-for", "")
    last = forwarded.rsplit(",", 1)[-1].strip()
    return last or client_host or "unknown"
