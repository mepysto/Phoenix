from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/tiles/{z}/{x}/{y}")
async def get_vector_tile(z: int, x: int, y: int) -> Response:
    return Response(content=b"", media_type="application/x-protobuf")
