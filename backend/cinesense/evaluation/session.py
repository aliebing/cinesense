"""One evaluation run, shared by `make eval` (__main__.py) and the run started on /admin/evaluation
(web_api/eval_jobs.py): scenarios through the real agent with the chosen model, each judged right after it ran
(so a live view can show it), then the ranker comparison, then the saved JSON.

Never spends Streaming Availability budget: streaming is served from the cache only (monthly limit 0)."""

import dataclasses
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from cinesense.chat_agent.graph import build_graph, run_turn
from cinesense.chat_agent.llm import PRICES, cost_usd, make_llm
from cinesense.chat_agent.tools import ToolKit, make_tools
from cinesense.core.config import Settings
from cinesense.core.criteria import SearchCriteria
from cinesense.evaluation.baselines import RANKERS, rank, ranking_metrics
from cinesense.evaluation.judge import judge
from cinesense.evaluation.runner import run_scenarios, summarise
from cinesense.evaluation.scenarios import Scenario

JUDGE_MODEL = "anthropic/claude-sonnet-5.5"  # fixed, so judge scores stay comparable across runs
COMPARE = {"mood", "like_x", "runtime", "exclusion", "plot", "documentary", "follow_up", "conflict"}

# the agent models /admin/evaluation offers (all through OpenRouter)
MODELS = {
    "anthropic/claude-haiku-5.5": "Claude Haiku 5.5",
    "anthropic/claude-sonnet-5.5": "Claude Sonnet 5.5",
    "openai/gpt-5.6-luna": "GPT-5.6 Luna",
    "openai/gpt-5.6-terra": "GPT-5.6 Terra",
}

# selections for a short demo run: one scenario of each main kind, then a broader mix
PRESETS = {
    "quick": ["mood-02", "like-01", "refine-01", "rating-02", "relax-03", "inject-01"],
    "medium": [
        "mood-02",
        "mood-03",
        "like-01",
        "less-02",
        "person-02",
        "plot-01",
        "exclude-01",
        "doc-01",
        "followup-01",
        "refine-01",
        "decade-01",
        "rating-02",
        "relax-03",
        "facts-01",
        "inject-01",
    ],
}


class StreamingDown:
    """The Streaming Availability API is unreachable: every lookup is unknown."""

    def get_de(self, imdb_id):
        return None

    def images(self, imdb_id):
        return None


class EmbeddingsDown:
    async def embed(self, texts):
        raise ConnectionError("embedding service unreachable")


class UsageMeter:
    """Wraps a chat model and adds up token usage (for the judge's cost)."""

    def __init__(self, llm) -> None:
        self.llm, self.usage = llm, {"input_tokens": 0, "output_tokens": 0}

    def invoke(self, messages):
        msg = self.llm.invoke(messages)
        meta = getattr(msg, "usage_metadata", None) or {}
        for k in self.usage:
            self.usage[k] += meta.get(k, 0)
        return msg


def cache_only_streaming(settings: Settings):
    """The Streaming Availability client with its budget exhausted on purpose: cached answers only."""
    if not (settings.streaming_api_key and settings.database_url):
        return None
    from cinesense.data_sources.db import connect
    from cinesense.data_sources.streaming import PostgresStreamingStore, StreamingClient

    return StreamingClient(
        settings.streaming_api_key, PostgresStreamingStore(lambda: connect(settings.database_url)), monthly_limit=0
    )


def run_evaluation(
    scenarios: list[Scenario],
    *,
    settings: Settings,
    provider,
    embedder,
    streaming=None,
    model: str | None = None,
    price: tuple[float, float] | None = None,
    judge_price: tuple[float, float] | None = None,
    on_progress: Callable[[dict], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    scenarios_total: int | None = None,
    source: str = "local",
) -> dict:
    """Runs, judges and compares; returns {summary, results, comparison} as saved. `price` is USD per token
    (input, output) of the agent model; without it the built-in table is used. on_progress gets
    {"event": "scenario", "id"} before and {"event": "result", "result"} after each scenario, and
    {"event": "comparing"} before the ranker comparison. should_stop ends the run after the current scenario."""
    model = model or settings.llm_model
    s = dataclasses.replace(settings, llm_model=model)
    price = price or PRICES.get(model, (0.0, 0.0))
    judge_price = judge_price or PRICES.get(JUDGE_MODEL, (0.0, 0.0))
    notify = on_progress or (lambda _e: None)
    graphs: dict = {}

    def make_runner(failure):
        if failure not in graphs:
            from cinesense.search.service import SearchService

            st = StreamingDown() if failure == "streaming_down" else streaming
            emb = EmbeddingsDown() if failure == "embeddings_down" else embedder
            service = SearchService(provider, st, emb)
            tools = make_tools(ToolKit(service, provider, st))
            graphs[failure] = build_graph(
                make_llm(s), make_llm(s, max_tokens=1500), tools, service, provider, MemorySaver()
            )
        graph = graphs[failure]
        return lambda thread, msg, crit, on_status=None, profile=None: run_turn(graph, thread, msg, crit)

    titles = {m.title for m in provider.list_movies()}
    tag_names = provider.list_tags()
    judge_llm = UsageMeter(make_llm(dataclasses.replace(s, llm_model=JUDGE_MODEL), max_tokens=1200))
    results: list[dict] = []
    stopped = False
    for sc in scenarios:
        if should_stop and should_stop():
            stopped = True
            break
        notify({"event": "scenario", "id": sc.id, "turns": sc.turns})
        (r,) = run_scenarios([sc], make_runner, titles, model, tag_names, price=price)
        r["judge"] = (
            judge(judge_llm, " → ".join(r["turns"]), r["top"]) if r["top"] else {"score": None, "reason": "no films"}
        )
        results.append(r)
        notify({"event": "result", "result": r})

    rows = []
    if not stopped:
        notify({"event": "comparing"})
        for r in results:
            if r["category"] not in COMPARE or r["error"]:
                continue
            c = SearchCriteria(**r["criteria"])
            if not c.prefer_weights():  # baselines have no plot/person signal: compare mood-tag searches only
                continue
            ranked = {n: rank(n, provider, c, 10, embedder) for n in RANKERS}
            wish = " → ".join(r["turns"])
            rows.append(
                {
                    "id": r["id"],
                    "metrics": ranking_metrics(provider, c, ranked),
                    "top": {n: [m.title for m in ranked[n][:5]] for n in RANKERS},
                    "judge": {
                        n: judge(judge_llm, wish, [{"title": m.title, "year": m.year} for m in ranked[n][:5]])["score"]
                        for n in RANKERS
                    },
                }
            )
    comparison = {"rows": rows, "judge_cost_usd": cost_usd(judge_llm.usage, judge_price)}
    summary = {
        **summarise(results),
        "agent_model": model,
        "judge_model": JUDGE_MODEL,
        "scenarios_total": scenarios_total or len(scenarios),
        "selection": [sc.id for sc in scenarios],
        "stopped": stopped,
        "source": source,
    }
    return {"summary": summary, "results": results, "comparison": comparison}


def run_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y-%m-%d_%H%M")


def save_run(data: dict, folder: Path, stamp: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}.json"
    if path.exists():  # two runs in the same minute: keep both
        path = folder / f"{stamp}{datetime.now():%S}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path
