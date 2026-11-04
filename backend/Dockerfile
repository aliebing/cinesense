# CineSense API (FastAPI + LangGraph agent). Talks to the Supabase catalogue; secrets come from .env at runtime.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY cinesense ./cinesense
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
COPY entrypoint.sh /usr/local/bin/api-entrypoint
EXPOSE 8000
ENTRYPOINT ["api-entrypoint"]
CMD ["uvicorn", "cinesense.web_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
