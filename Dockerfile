FROM node:24-slim AS frontend
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
RUN useradd --create-home appuser
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app/ app/
COPY --from=frontend /web/dist web/dist
RUN mkdir data && chown appuser:appuser data
USER appuser
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
