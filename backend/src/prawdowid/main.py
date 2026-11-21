import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from prawdowid.api import admin, checks, health, sources
from prawdowid.config import Settings, get_settings
from prawdowid.services import ServiceOverrides, get_services

logger = logging.getLogger(__name__)


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
    if resolved_settings.web_dist_path.exists():
        app.mount(
            "/", StaticFiles(directory=resolved_settings.web_dist_path, html=True), name="web"
        )
    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("prawdowid.main:create_app", factory=True, host="0.0.0.0", port=8000)  # noqa: S104
