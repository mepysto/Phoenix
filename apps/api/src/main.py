import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.v1 import (
    admin,
    agent,
    cameras,
    events,
    geodata,
    hazards,
    infrastructure,
    sources,
    sync,
    tracks,
    websocket,
)
from src.core.config import settings
from src.core.exceptions import DataSyncError, ExternalAPIError
from src.core.security import verify_api_key
from src.services.scheduler import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _start_ais_stream() -> None:
    from websockets.asyncio.client import connect

    from src.db.database import async_session_maker
    from src.services.tracks.vessels import STREAM_URL, VesselStream

    assert settings.aisstream_api_key is not None
    stream = VesselStream(
        api_key=settings.aisstream_api_key.get_secret_value(),
        sessions=async_session_maker,
        connect=lambda: connect(STREAM_URL, compression="deflate", open_timeout=10),
        max_boxes=settings.ais_max_boxes,
        box_degrees=settings.ais_box_degrees,
    )
    await stream.run_forever()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Phoenix API...")
    initial_sync: asyncio.Task[None] | None = None
    ais_stream: asyncio.Task[None] | None = None
    if settings.scheduler_enabled and settings.aisstream_api_key:
        # One AIS connection per deployment: it lives with the scheduler
        ais_stream = asyncio.create_task(_start_ais_stream())
    if settings.scheduler_enabled:
        # Initial sync runs in the background: a slow or unreachable feed must
        # not block startup (it took up to ~47s with retries).
        initial_sync = asyncio.create_task(scheduler_service.sync_gdacs())
        scheduler_service.start(sync_interval_minutes=5)
    yield
    for task in (initial_sync, ais_stream):
        if task is not None and not task.done():
            task.cancel()
    if settings.scheduler_enabled:
        scheduler_service.stop()
    logger.info("Phoenix API shutdown complete")


app = FastAPI(
    title="Phoenix API",
    description="Humanitarian Digital Twin Platform API",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Models built inside endpoints (e.g. EventFilter) are client input errors."""
    errors = exc.errors(include_url=False, include_context=False)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


@app.exception_handler(ExternalAPIError)
@app.exception_handler(DataSyncError)
async def upstream_error_handler(request: Request, exc: ExternalAPIError) -> JSONResponse:
    """Upstream data source failures are gateway errors, not internal bugs."""
    logger.warning("Upstream failure on %s: %s", request.url.path, exc.message)
    return JSONResponse(status_code=502, content={"detail": "Upstream data source unavailable"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(geodata.router, prefix="/api/v1/geodata", tags=["GeoData"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["Sync"])
app.include_router(sources.router, prefix="/api/v1/sources", tags=["Sources"])
app.include_router(hazards.router, prefix="/api/v1/hazards", tags=["Hazards"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(tracks.router, prefix="/api/v1/tracks", tags=["Tracks"])
app.include_router(cameras.router, prefix="/api/v1/cameras", tags=["Cameras"])
app.include_router(
    infrastructure.router, prefix="/api/v1/infrastructure", tags=["Infrastructure"]
)
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_api_key)],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/scheduler/status", dependencies=[Depends(verify_api_key)])
async def scheduler_status() -> dict:
    return scheduler_service.get_status()
