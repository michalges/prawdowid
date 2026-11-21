import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prawdowid.api import admin, checks, health, sources
from prawdowid.config import Settings, get_settings
from prawdowid.core.guards import SECONDS_PER_MINUTE
from prawdowid.services import ServiceOverrides, Services, get_services

logger = logging.getLogger(__name__)


def run_retention_purge(services: Services) -> None:
    try:
        removed = services.database.purge_older_than(services.settings.retention_days)
        if removed:
            services.pipeline.cache.clear()
        if services.pipeline.rate_limiter:
            services.pipeline.rate_limiter.purge_expired()
        logger.info("Retention purge removed %d rows", removed)
    except Exception:
        logger.exception("Retention purge failed")


async def purge_periodically(services: Services) -> None:
    interval = services.settings.retention_purge_interval_minutes * SECONDS_PER_MINUTE
    while True:
        await asyncio.sleep(interval)
        run_retention_purge(services)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    services = app.state.services
    run_retention_purge(services)
    purge_task = asyncio.create_task(purge_periodically(services), name="retention-purge")
    try:
        yield
    finally:
        purge_task.cancel()
        with suppress(asyncio.CancelledError):
            await purge_task


def create_app(
    settings: Settings | None = None, overrides: ServiceOverrides | None = None
) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="Prawdowid API",
        description=(
            "Source-based verification of claims with citations and honest abstention. "
            "All channels (web, Discord, demo chat, mobile) use POST /v1/checks."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.services = get_services(resolved_settings, overrides)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in resolved_settings.cors_origins.split(",")],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(checks.router)
    app.include_router(sources.router)
    app.include_router(admin.router)
    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("prawdowid.main:create_app", factory=True, host="0.0.0.0", port=8000)  # noqa: S104
