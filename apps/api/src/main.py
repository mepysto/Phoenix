import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import events, geodata, sync
from src.core.config import settings
from src.services.scheduler import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Phoenix API...")
    await scheduler_service.sync_gdacs()
    scheduler_service.start(sync_interval_minutes=5)
    yield
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


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/scheduler/status")
async def scheduler_status() -> dict[str, str | int | None]:
    return scheduler_service.get_status()
