"""The evaluation run started on /admin/evaluation: one at a time, in a background thread of the API process,
with a state the page polls (which scenario runs, each result as it comes, the cost so far). The finished run is
saved like a `make eval` run (CINESENSE_EVAL_RUNS_DIR) and shows up in the run list."""

import logging
import threading
import time
from collections.abc import Callable

log = logging.getLogger(__name__)


class Busy(Exception):
    """A run is already going."""


def compact(r: dict) -> dict:
    """What the live view shows of one finished scenario."""
    return {
        "id": r["id"],
        "category": r["category"],
        "turns": r["turns"],
        "passed": r["passed"],
        "reply": r.get("reply", ""),
        "results": r.get("results", [])[:5],
        "judge": r.get("judge"),
        "latency_s": r.get("latency_s"),
        "cost_usd": r.get("cost_usd"),
        "error": r.get("error"),
        "failed_checks": [k for k, c in (r.get("checks") or {}).items() if not c["ok"]],
        "grounding_fallback": r.get("grounding_fallback", False),
    }


class EvalJob:
    """`work(model, scenario_ids, on_progress, should_stop) -> run id` does the run (wired in deps/eval_view);
    this class only keeps the state and makes sure there is one run at a time."""

    def __init__(self, work: Callable, clock: Callable[[], float] = time.time) -> None:
        self._work = work
        self._clock = clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._state: dict = {"status": "idle"}

    def snapshot(self) -> dict:
        with self._lock:
            s = dict(self._state)
            s["results"] = list(s.get("results", []))
            return s

    def start(self, model: str, scenario_ids: list[str], background: bool = True) -> dict:
        with self._lock:
            if self._state["status"] in ("running", "stopping"):
                raise Busy
            self._stop.clear()
            self._state = {
                "status": "running",
                "model": model,
                "selection": scenario_ids,
                "total": len(scenario_ids),
                "done": 0,
                "passed": 0,
                "cost_usd": 0.0,
                "current": None,
                "phase": "scenarios",
                "results": [],
                "started": self._clock(),
                "run": None,
                "error": None,
            }
        if background:
            threading.Thread(target=self._run, args=(model, scenario_ids), name="eval-run", daemon=True).start()
        else:
            self._run(model, scenario_ids)
        return self.snapshot()

    def stop(self) -> dict:
        with self._lock:
            if self._state["status"] == "running":
                self._stop.set()
                self._state["status"] = "stopping"
        return self.snapshot()

    def _progress(self, e: dict) -> None:
        with self._lock:
            if e["event"] == "scenario":
                self._state["current"] = {"id": e["id"], "turns": e.get("turns", [])}
            elif e["event"] == "result":
                r = e["result"]
                self._state["results"].append(compact(r))
                self._state["done"] += 1
                self._state["passed"] += bool(r["passed"])
                self._state["cost_usd"] = round(self._state["cost_usd"] + (r.get("cost_usd") or 0), 6)
                self._state["current"] = None
            elif e["event"] == "comparing":
                self._state["phase"] = "comparing"

    def _run(self, model: str, scenario_ids: list[str]) -> None:
        try:
            run = self._work(model, scenario_ids, self._progress, self._stop.is_set)
            with self._lock:
                self._state.update(
                    status="stopped" if self._stop.is_set() else "done", run=run, current=None, phase="saved"
                )
        except Exception as exc:  # noqa: BLE001 — the page shows it; the API keeps running
            log.exception("evaluation run failed")
            with self._lock:
                self._state.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:300], current=None)
