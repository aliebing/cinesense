"""Persistent 👍/👎 per anonymous user id (a random UUID from the browser; no personal data)."""

import threading


class MemoryFeedbackStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, int]] = {}
        self._lock = threading.Lock()

    def set(self, user: str, film_id: str, value: int) -> None:
        with self._lock:
            films = self._data.setdefault(user, {})
            if value == 0:
                films.pop(film_id, None)
            else:
                films[film_id] = value

    def get(self, user: str) -> dict[str, int]:
        with self._lock:
            return dict(self._data.get(user, {}))

    def clear(self, user: str) -> None:
        with self._lock:
            self._data.pop(user, None)


class PostgresFeedbackStore:
    def __init__(self, conn_factory) -> None:
        self._conn = conn_factory

    def set(self, user: str, film_id: str, value: int) -> None:
        with self._conn() as c:
            if value == 0:
                c.execute("delete from feedback where user_id = %s and film_id = %s", (user, film_id))
            else:
                c.execute(
                    "insert into feedback (user_id, film_id, value) values (%s, %s, %s) on conflict (user_id, film_id) "
                    "do update set value = excluded.value, updated_at = now()",
                    (user, film_id, value),
                )
            c.commit()

    def get(self, user: str) -> dict[str, int]:
        with self._conn() as c:
            rows = c.execute(
                "select film_id, value from feedback where user_id = %s order by updated_at", (user,)
            ).fetchall()
        return {r[0]: int(r[1]) for r in rows}

    def clear(self, user: str) -> None:
        with self._conn() as c:
            c.execute("delete from feedback where user_id = %s", (user,))
            c.commit()
