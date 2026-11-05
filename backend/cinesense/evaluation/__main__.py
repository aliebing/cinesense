"""Live evaluation: uv run python -m cinesense.evaluation  (needs SUPABASE_DB_URL and OPENROUTER_API_KEY).

Runs every scenario with the configured model (session.py) and writes evaluation/results/<stamp>.json and
evaluation/REPORT.md. Never spends Streaming Availability budget: streaming is served from the cache only."""

import json
import logging

from cinesense.core.config import REPO_ROOT, get_settings, load_env_file
from cinesense.data_sources.db import connect
from cinesense.data_sources.embeddings import EmbeddingClient
from cinesense.data_sources.postgres import PostgresProvider
from cinesense.evaluation.report import render_report
from cinesense.evaluation.scenarios import load_scenarios
from cinesense.evaluation.session import cache_only_streaming, run_evaluation, run_stamp, save_run

OUT_DIR = REPO_ROOT / "evaluation"


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    load_env_file()
    s = get_settings()
    if not (s.database_url and s.openrouter_api_key):
        raise SystemExit("SUPABASE_DB_URL and OPENROUTER_API_KEY are required")
    provider = PostgresProvider(lambda: connect(s.database_url))
    scenarios = load_scenarios()
    print(f"Running {len(scenarios)} scenarios …", flush=True)

    def progress(e: dict) -> None:
        if e["event"] == "result":
            r = e["result"]
            print(f"  {'pass' if r['passed'] else 'FAIL'} {r['id']}", flush=True)

    data = run_evaluation(
        scenarios,
        settings=s,
        provider=provider,
        embedder=EmbeddingClient(s.openrouter_api_key),
        streaming=cache_only_streaming(s),
        on_progress=progress,
    )
    stamp = run_stamp()
    save_run(data, OUT_DIR / "results", stamp)
    summary, comparison = data["summary"], data["comparison"]
    (OUT_DIR / "REPORT.md").write_text(render_report(summary, data["results"], comparison, stamp[:10], s.llm_model))
    print(json.dumps(summary, indent=2))
    print(f"Judge cost ${comparison['judge_cost_usd']:.3f}; report: evaluation/REPORT.md")


if __name__ == "__main__":
    main()
