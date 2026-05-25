FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "python", "-m", "app.main"]
