from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.aura import router as aura_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.spaces import router as spaces_router
from app.api.routes.team import router as team_router
from app.api.routes.timetravel import router as timetravel_router
from app.core.config import get_settings
from app.db import init_db
from app.grpc.server import build_core_logic_grpc_server


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    settings = get_settings()
    grpc_server = None
    if settings.start_embedded_core_logic_grpc:
        grpc_server = build_core_logic_grpc_server()
        grpc_server.add_insecure_port(settings.embedded_core_logic_grpc_bind)
        grpc_server.start()
    yield
    if grpc_server is not None:
        grpc_server.stop(grace=None)


def create_app() -> FastAPI:
    app = FastAPI(
        title="SwarmPM Mike Backend",
        version="0.1.0",
        description="Milestone-aligned backend scaffold for Mike L.",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(spaces_router)
    app.include_router(dashboard_router)
    app.include_router(team_router)
    app.include_router(aura_router)
    app.include_router(timetravel_router)

    return app


app = create_app()
