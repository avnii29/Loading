import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass
class StoredFile:
    key: str
    mime_type: str
    byte_size: int


class StorageProvider:
    def save(self, upload: UploadFile) -> StoredFile:
        raise NotImplementedError

    def resolve_path(self, key: str) -> Path:
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = settings.max_upload_bytes
        self.allowed = settings.allowed_upload_types

    def save(self, upload: UploadFile) -> StoredFile:
        mime = (upload.content_type or "").lower()
        if mime not in self.allowed:
            raise HTTPException(status_code=422, detail="That photo type is not supported.")
        ext = MIME_TO_EXT.get(mime)
        if not ext:
            raise HTTPException(status_code=422, detail="That photo type is not supported.")

        data = upload.file.read()
        if not data:
            raise HTTPException(status_code=422, detail="The photo file is empty.")
        if len(data) > self.max_bytes:
            raise HTTPException(status_code=422, detail="That photo is too large. Use an image under 5 MB.")

        key = f"{uuid.uuid4().hex}{ext}"
        dest = self.root / key
        dest.write_bytes(data)
        return StoredFile(key=key, mime_type=mime, byte_size=len(data))

    def resolve_path(self, key: str) -> Path:
        safe = os.path.basename(key)
        path = (self.root / safe).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise HTTPException(status_code=404, detail="Photo not found.")
        if not path.exists():
            raise HTTPException(status_code=404, detail="Photo not found.")
        return path


storage_provider = LocalStorageProvider()
