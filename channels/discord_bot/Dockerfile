# Build from channels/discord_bot/:  docker build -t prawdowid-discord channels/discord_bot
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY prawdowid_discord ./prawdowid_discord
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "prawdowid_discord"]
