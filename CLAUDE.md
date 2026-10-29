# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

CineSense AI is at the scaffold stage: a `uv init` Python project (`main.py` is a hello-world placeholder, no dependencies, no tests, empty `README.md`). Architecture is still to be designed, so check with the user before committing to frameworks or structure.

## Context: what this project is for

This is a Turing College AI Engineering project. The two briefs in the repo root define the requirements and grading:

- `turing-college-sprint4.md` — build an AI **agent** app (LangGraph/LangChain, function calling, short/long-term memory, Streamlit or Next.js UI). Bonus points need at least 2 "medium" and 1 "hard" optional tasks.
- `turing-college-capstone.md` — capstone cases (RAG, agents, document search, multi-modal, etc.) and evaluation criteria (ethics/privacy, prompt engineering, presentation).

Both require a `README.md` that concisely explains the project's goal, the problem it solves, and how it works, plus usage docs and examples. The capstone also expects a showcase.turingcollege.com link near the top of the README.

## Planned stack (from `.env`)

The environment variables already configured point to the intended services:

- **Supabase** (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_DB_URL`): database / likely pgvector and memory storage
- **OpenRouter** (`OPENROUTER_API_KEY`): LLM access (`OPENAI_API_KEY` is commented out)
- **LangSmith** (`LANGSMITH_*`): tracing, on the **EU** endpoint

## Commands

The project uses `uv` with Python 3.12 (`.python-version`).

```bash
uv sync                 # create .venv and install dependencies
uv add <package>        # add a dependency (updates pyproject.toml + uv.lock)
uv run main.py          # run the entry point
```
