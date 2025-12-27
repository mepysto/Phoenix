from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from src.core.config import settings
from src.services.gdacs_service import GDACSService

router = APIRouter()


def verify_sync_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_api_key != settings.api_sync_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/gdacs", dependencies=[Depends(verify_sync_key)])
async def sync_gdacs() -> dict:
    service = GDACSService()
    result = await service.sync_events()
    return {"status": "completed", "synced": result}


@router.post("/copernicus", dependencies=[Depends(verify_sync_key)])
async def sync_copernicus() -> dict:
    return {"status": "not_implemented"}
