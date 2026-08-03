FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless the lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

EXPOSE 8000

CMD ["sh", "-c", "uv run manage.py migrate && uv run manage.py runserver 0.0.0.0:8000"]
