from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.database import get_db
from src.services.connectors.eonet_connector import EONETConnector
from src.services.connectors.usgs_connector import USGSConnector
from src.services.copernicus_service import CopernicusEMSService
from src.services.gdacs_service import GDACSService
from src.services.ingestion_service import IngestionService

router = APIRouter()


def verify_sync_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_api_key != settings.api_sync_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/gdacs", dependencies=[Depends(verify_sync_key)])
async def sync_gdacs(session: AsyncSession = Depends(get_db)) -> dict:
    """Sync GDACS events and store to database.

    Fetches events from GDACS RSS feed and ingests them into the database.
    Uses upsert logic to handle duplicates.

    Returns:
        Status with created/updated/failed counts
    """
    gdacs_service = GDACSService()
    events = await gdacs_service.fetch_rss_events()

    ingestion_service = IngestionService(session)
    result = await ingestion_service.ingest_gdacs_events(events)

    return {"status": "success", "result": result}


@router.post("/copernicus", dependencies=[Depends(verify_sync_key)])
async def sync_copernicus(session: AsyncSession = Depends(get_db)) -> dict:
    """Sync Copernicus EMS events and store to database.

    Fetches activations from Copernicus EMS API and ingests them into the database.
    Uses upsert logic to handle duplicates.

    Returns:
        Status with created/updated/failed counts
    """
    copernicus_service = CopernicusEMSService()
    events = await copernicus_service.fetch_activations()

    ingestion_service = IngestionService(session)
    result = await ingestion_service.ingest_copernicus_events(events)

    return {"status": "success", "result": result}


@router.post("/usgs", dependencies=[Depends(verify_sync_key)])
async def sync_usgs(
    feed: Annotated[
        str,
        Query(
            description="USGS feed to sync. Options: 4.5_day, 4.5_week, all_day, significant_month"
        ),
    ] = "4.5_week",
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Sync USGS earthquake data and store to database.

    Fetches earthquake events from USGS GeoJSON feed and ingests them into the database.
    Uses upsert logic to handle duplicates.

    Args:
        feed: USGS feed identifier. Available options:
            - 4.5_day: M4.5+ earthquakes from the past day
            - 4.5_week: M4.5+ earthquakes from the past week (default)
            - all_day: All earthquakes from the past day
            - significant_month: Significant earthquakes from the past month

    Returns:
        Status with created/updated/failed counts
    """
    connector = USGSConnector(feed=feed)
    events = await connector.fetch_events()

    ingestion_service = IngestionService(session)
    result = await ingestion_service.ingest_usgs_events(events)

    return {"status": "success", "result": result}


@router.post("/eonet", dependencies=[Depends(verify_sync_key)])
async def sync_eonet(
    status: Annotated[
        str,
        Query(description="Event status filter. Options: open, closed, all"),
    ] = "open",
    days: Annotated[
        int,
        Query(description="Fetch events from the last N days", ge=1, le=365),
    ] = 30,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Sync NASA EONET events and store to database.

    Fetches natural event data from NASA EONET API and ingests them into the database.
    Uses upsert logic to handle duplicates.

    Args:
        status: Event status filter:
            - open: Only ongoing events (default)
            - closed: Only closed/ended events
            - all: Both open and closed events
        days: Fetch events from the last N days (default: 30)

    Returns:
        Status with created/updated/failed counts
    """
    connector = EONETConnector(status=status, days=days)
    events = await connector.fetch_events()

    ingestion_service = IngestionService(session)
    result = await ingestion_service.ingest_eonet_events(events)

    return {"status": "success", "result": result}
