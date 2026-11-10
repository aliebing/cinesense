"""The operator's sign-in for /admin (as in HikeSense): name from TECH_USER, password checked against the bcrypt hash
in TECH_PASSWORD_HASH (`make admin-password`), then a
signed HttpOnly session cookie that the server also remembers, so signing out ends a copied cookie too. Five
failed attempts per address block the sign-in for 15 minutes. Sessions live in this process (one uvicorn worker);
a restart signs the operator out. No HTTP Basic Auth: the browser never shows its own login prompt."""

import hashlib
import hmac
import math
import secrets
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

import bcrypt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cinesense.core.config import get_settings
from cinesense.web_api.limits import visitor_of

COOKIE = "cs_admin"
SESSION_S = 8 * 3600
_SECRET = secrets.token_hex(32)  # per process: sessions end with a restart anyway


def _ascii_int(text: str) -> int | None:
    return int(text) if text and text.isascii() and text.isdigit() else None


class Sessions:
    """Cookies `exp.sid.sig` (HMAC over expiry and session id); the server keeps the live ids, so sign-out
    revokes. At most MAX at once, the oldest goes first."""

    MAX = 50

    def __init__(self) -> None:
        self._live: dict[str, int] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _sig(secret: str, exp: int, sid: str) -> str:
        return hmac.new(secret.encode(), f"admin:{exp}:{sid}".encode(), hashlib.sha256).hexdigest()

    def issue(self, secret: str, now: float) -> str:
        exp, sid = int(now) + SESSION_S, secrets.token_urlsafe(16)
        with self._lock:
            self._live = {k: e for k, e in self._live.items() if e > now}
            while len(self._live) >= self.MAX:
                self._live.pop(min(self._live, key=self._live.__getitem__))
            self._live[sid] = exp
        return f"{exp}.{sid}.{self._sig(secret, exp, sid)}"

    def valid(self, cookie: str | None, secret: str, now: float) -> bool:
        parts = (cookie or "").split(".")
        if len(parts) != 3:
            return False
        exp, sid, sig = _ascii_int(parts[0]), parts[1], parts[2]
        if exp is None or not sid or not sig or exp <= now:
            return False
        if not hmac.compare_digest(sig, self._sig(secret, exp, sid)):
            return False
        with self._lock:
            return self._live.get(sid) == exp

    def revoke(self, cookie: str | None) -> None:
        parts = (cookie or "").split(".")
        if len(parts) == 3:
            with self._lock:
                self._live.pop(parts[1], None)


class LoginThrottle:
    """At most `max_failures` attempts per address within `window_s`. An attempt is counted before the password
    check, so parallel requests cannot slip past the cap; a successful sign-in clears the address."""

    def __init__(self, max_failures: int = 5, window_s: float = 900, clock: Callable[[], float] = time.monotonic):
        self._max, self._window, self._clock = max_failures, window_s, clock
        self._fails: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def try_acquire(self, ip: str) -> int:
        """0 = go ahead, else the seconds until the next attempt is allowed."""
        with self._lock:
            now = self._clock()
            q = self._fails[ip]
            while q and q[0] <= now - self._window:
                q.popleft()
            if len(q) >= self._max:
                return max(1, math.ceil(q[0] + self._window - now))
            q.append(now)
            return 0

    def succeeded(self, ip: str) -> None:
        with self._lock:
            self._fails.pop(ip, None)


SESSIONS = Sessions()
THROTTLE = LoginThrottle()


def _same(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())


MAX_PASSWORD_BYTES = 72  # bcrypt refuses anything longer


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def check_password(password: str, bcrypt_hash: str) -> bool:
    raw = password.encode()
    if not bcrypt_hash or len(raw) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, bcrypt_hash.encode())
    except ValueError:  # not a bcrypt hash
        return False


def _configured() -> tuple[str, str] | None:
    """(user, hash); None only without TECH_USER (local development). A user without a valid hash keeps the admin
    closed: no password matches."""
    s = get_settings()
    return (s.tech_user, s.tech_password_hash or "") if s.tech_user else None


def _secure(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    return request.url.scheme == "https" or proto == "https"


def signed_in(request: Request) -> bool:
    if _configured() is None:
        return True  # no login configured: local development
    return SESSIONS.valid(request.cookies.get(COOKIE), _SECRET, time.time())


def require_tech_login(request: Request) -> None:
    """Guards the admin API (/api/admin, /api/inspect, /api/eval) with the session cookie."""
    if not signed_in(request):
        raise HTTPException(status_code=401, detail="login_required")


class LoginBody(BaseModel):
    name: str = Field(max_length=200)
    password: str = Field(max_length=200)


router = APIRouter(prefix="/api/admin")


@router.post("/login")
def login(body: LoginBody, request: Request) -> JSONResponse:
    configured = _configured()
    if configured is None:
        return JSONResponse({"name": "local"})  # nothing to sign in to locally
    ip = visitor_of(request.headers, request.client and request.client.host)
    wait = THROTTLE.try_acquire(ip)
    if wait:
        return JSONResponse({"detail": "too_many_attempts"}, status_code=429, headers={"Retry-After": str(wait)})
    name_ok = _same(body.name.strip(), configured[0])
    if not (check_password(body.password, configured[1]) and name_ok):
        return JSONResponse({"detail": "login_failed"}, status_code=401)
    THROTTLE.succeeded(ip)
    r = JSONResponse({"name": configured[0]})
    r.set_cookie(
        COOKIE,
        SESSIONS.issue(_SECRET, time.time()),
        max_age=SESSION_S,
        httponly=True,
        samesite="strict",
        secure=_secure(request),
        path="/",
    )
    return r


@router.post("/logout")
def logout(request: Request) -> JSONResponse:
    SESSIONS.revoke(request.cookies.get(COOKIE))  # a copied cookie stops working too
    r = JSONResponse({"ok": True})
    r.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=_secure(request))
    return r


@router.get("/me")
def me(request: Request) -> JSONResponse:
    if not signed_in(request):
        return JSONResponse({"detail": "login_required"}, status_code=401)
    configured = _configured()
    return JSONResponse({"name": configured[0] if configured else "local"})


def main() -> int:
    """`make admin-password`: asks for the password twice and prints the .env line; writes nothing."""
    import getpass
    import sys

    pw = getpass.getpass("New admin password: ")
    if len(pw) < 8 or len(pw.encode()) > MAX_PASSWORD_BYTES:
        print("The password needs 8 to 72 bytes.", file=sys.stderr)
        return 2
    if getpass.getpass("Again: ") != pw:
        print("The two entries differ.", file=sys.stderr)
        return 2
    print("Put into .env (single quotes because of the $ signs):")
    print(f"TECH_PASSWORD_HASH='{hash_password(pw)}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
