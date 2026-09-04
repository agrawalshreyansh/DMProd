import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.instagram import router as instagram_router
from app.api.integrations import router as integrations_router
from app.api.preferences import router as preferences_router
from app.api.reels import router as reels_router
from app.api.settings_routes import router as settings_router
from app.api.stats import router as stats_router
from app.api.tasks import router as tasks_router
from app.api.webhooks import router as webhooks_router
from app.config import settings
from app.db import init_db

# Without this, app-level logger.info() calls (e.g. webhooks.instagram) are
# silently dropped — the root logger has no handler by default, and
# uvicorn's own dictConfig only touches its own "uvicorn.*" loggers, not
# root. Basic stream-to-stdout is enough for dev; Phase 11 replaces this
# with real structured logging/Sentry.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Panda API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(settings_router)
    app.include_router(webhooks_router)
    app.include_router(instagram_router)
    app.include_router(reels_router)
    app.include_router(stats_router)
    app.include_router(tasks_router)
    app.include_router(integrations_router)
    app.include_router(preferences_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
