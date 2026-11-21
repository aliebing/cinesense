"""Which film is meant? The chat model may only guess titles; each guess must exist (looked up in a source) and its
real plot, from the source and never from the model's memory, must match the user's description."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import HumanMessage, SystemMessage

from cinesense.chat_agent.prompts import PLOT_MATCH_PROMPT
from cinesense.core.models import Movie

log = logging.getLogger(__name__)
MAX_CANDIDATES = 5

Judge = Callable[[str, str], bool]


def make_plot_judge(llm) -> Judge:
    """(description, plot) -> whether the plot is the story described; on any error: no match."""

    def judge(description: str, plot: str) -> bool:
        if not plot.strip():
            return False
        try:
            msg = llm.invoke(
                [
                    SystemMessage(PLOT_MATCH_PROMPT),
                    HumanMessage(f"Description: {description}\n\nPlot from Wikipedia:\n{plot}"),
                ]
            )
        except Exception as exc:  # noqa: BLE001 — unverified means not shown
            log.warning("plot judge failed: %s", exc)
            return False
        return str(msg.content).strip().lower().startswith("yes")

    return judge


def check_candidates(
    description: str, candidates: list[tuple[str, int | None]], lookup, judge: Judge
) -> list[tuple[str, int | None, Movie | None, str, str]]:
    """Each candidate (title, year) -> (title, year, film, plot, verdict), in the given order; verdict is 'match',
    'no match' (the real plot tells another story) or 'not found' (no such film in the source)."""

    def one(cand: tuple[str, int | None]):
        title, year = cand
        hit = lookup.find(title, year)
        if hit is None:
            return title, year, None, "", "not found"
        film, plot = hit
        return title, year, film, plot, "match" if judge(description, plot) else "no match"

    cands = candidates[:MAX_CANDIDATES]
    with ThreadPoolExecutor(max_workers=len(cands) or 1) as pool:
        return list(pool.map(one, cands))
