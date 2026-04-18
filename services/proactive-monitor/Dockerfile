FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen || uv sync
COPY . .
CMD ["uv", "run", "celery", "-A", "app.worker", "worker", "-l", "info", "-Q", "proactive"]
