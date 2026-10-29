"""Live evaluation: uv run python -m cinesense.eval  (needs SUPABASE_DB_URL and OPENROUTER_API_KEY).

Never spends Streaming Availability budget: streaming is served from the cache only (monthly limit 0).
"""

import dataclasses
import json
import logging
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from cinesense.agent.graph import build_graph, run_turn
from cinesense.agent.llm import make_llm
from cinesense.agent.tools import ToolKit, make_tools
from cinesense.api.deps import get_embedder, get_provider
from cinesense.config import get_settings, load_env_file
from cinesense.domain.criteria import SearchCriteria
from cinesense.eval.baselines import RANKERS, rank, ranking_metrics
from cinesense.eval.judge import judge
from cinesense.eval.report import render_report
from cinesense.eval.runner import PRICES, cost_usd, run_scenarios, summarise
from cinesense.eval.scenarios import load_scenarios

OUT_DIR = Path(__file__).resolve().parents[3] / "eval"
JUDGE_MODEL = "anthropic/claude-sonnet-5.5"
COMPARE = {"mood", "like_x", "runtime", "exclusion", "plot", "documentary", "follow_up", "conflict"}
log = logging.getLogger("cinesense.eval")


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


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    load_env_file()
    s = get_settings()
    if not (s.database_url and s.openrouter_api_key):
        raise SystemExit("SUPABASE_DB_URL and OPENROUTER_API_KEY are required")
    provider, embedder = get_provider(), get_embedder()
    cache_only = None
    if s.streaming_api_key:
        from cinesense.db import connect
        from cinesense.providers.streaming import PostgresStreamingStore, StreamingClient

        cache_only = StreamingClient(
            s.streaming_api_key, PostgresStreamingStore(lambda: connect(s.database_url)), monthly_limit=0
        )  # budget exhausted on purpose: cached answers only

    graphs: dict = {}

    def make_runner(failure):
        if failure not in graphs:
            from cinesense.search.service import SearchService

            streaming = StreamingDown() if failure == "streaming_down" else cache_only
            emb = EmbeddingsDown() if failure == "embeddings_down" else embedder
            service = SearchService(provider, streaming, emb)
            tools = make_tools(ToolKit(service, provider, streaming))
            graphs[failure] = build_graph(
                make_llm(s), make_llm(s, max_tokens=1500), tools, service, provider, MemorySaver()
            )
        graph = graphs[failure]
        return lambda thread, msg, crit, on_status=None, profile=None: run_turn(graph, thread, msg, crit)

    scenarios = load_scenarios()
    titles = {m.title for m in provider.list_movies()}
    print(f"Running {len(scenarios)} scenarios …", flush=True)
    results = run_scenarios(scenarios, make_runner, titles, s.llm_model)

    judge_llm = UsageMeter(make_llm(dataclasses.replace(s, llm_model=JUDGE_MODEL), max_tokens=1200))
    for r in results:
        r["judge"] = (
            judge(judge_llm, " → ".join(r["turns"]), r["top"]) if r["top"] else {"score": None, "reason": "no films"}
        )
    rows = []
    for r in results:
        if r["category"] not in COMPARE or r["error"]:
            continue
        c = SearchCriteria(**r["criteria"])
        if not (c.has_tags() or c.plot_query):
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
    comparison = {"rows": rows, "judge_cost_usd": cost_usd(judge_llm.usage, PRICES[JUDGE_MODEL])}
    summary = summarise(results)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    (OUT_DIR / "results").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "results" / f"{stamp}.json").write_text(
        json.dumps({"summary": summary, "results": results, "comparison": comparison}, indent=2, ensure_ascii=False)
    )
    (OUT_DIR / "REPORT.md").write_text(render_report(summary, results, comparison, stamp[:10]))
    print(json.dumps(summary, indent=2))
    print(f"Judge cost ${comparison['judge_cost_usd']:.3f}; report: eval/REPORT.md")


if __name__ == "__main__":
    main()
