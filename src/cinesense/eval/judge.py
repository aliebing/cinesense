"""LLM-as-judge relevance (subjective, reported separately and labelled as such)."""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

JUDGE_PROMPT = """You rate film recommendations. Given a viewer's wish and a ranked list of films, rate how well
the list as a whole fits the wish on a 1-5 scale (5 = an excellent, fitting list; 1 = mostly unrelated).
Use your general film knowledge. Answer ONLY with JSON: {"score": <1-5>, "reason": "<one sentence>"}"""


def judge(llm, wish: str, films: list[dict]) -> dict:
    if not films:
        return {"score": None, "reason": "no films"}
    listing = "\n".join(
        f"{i + 1}. {f['title']}" + (f" ({f['year']})" if f.get("year") else "") for i, f in enumerate(films)
    )
    try:
        text = str(llm.invoke([SystemMessage(JUDGE_PROMPT), HumanMessage(f"Wish: {wish}\nFilms:\n{listing}")]).content)
    except Exception as exc:  # noqa: BLE001
        return {"score": None, "reason": f"judge failed: {type(exc).__name__}"}
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
        score = int(data.get("score"))
    except (ValueError, TypeError):
        return {"score": None, "reason": "unparseable judge output"}
    if not 1 <= score <= 5:
        return {"score": None, "reason": "score out of range"}
    return {"score": score, "reason": str(data.get("reason", ""))[:300]}
