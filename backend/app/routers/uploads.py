from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.storage import storage_provider

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.get("/{key}")
def get_upload(key: str):
    path = storage_provider.resolve_path(key)
    return FileResponse(path)
