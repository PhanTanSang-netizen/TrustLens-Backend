import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@dataclass
class StoredFileData:
    original_name: str
    stored_name: str
    stored_path: str
    mime_type: str
    extension: str
    size_bytes: int
    checksum: str


async def validate_and_store_upload_file(
    upload_file: UploadFile,
) -> StoredFileData:
    original_name = upload_file.filename

    if original_name is None or original_name.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_NAME_MISSING",
                "message": "File upload thiếu tên file.",
                "details": None,
            },
        )

    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_EXTENSION_NOT_SUPPORTED",
                "message": "Hệ thống chỉ hỗ trợ file PDF hoặc DOCX.",
                "details": {
                    "allowed_extensions": list(ALLOWED_EXTENSIONS.keys()),
                    "received_extension": suffix,
                },
            },
        )

    expected_mime_type = ALLOWED_EXTENSIONS[suffix]
    received_mime_type = upload_file.content_type or "application/octet-stream"

    if received_mime_type != expected_mime_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_MIME_TYPE_NOT_SUPPORTED",
                "message": "MIME type của file không hợp lệ.",
                "details": {
                    "expected_mime_type": expected_mime_type,
                    "received_mime_type": received_mime_type,
                },
            },
        )

    content = await upload_file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_EMPTY",
                "message": "File upload đang rỗng.",
                "details": None,
            },
        )

    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": "File vượt quá dung lượng cho phép.",
                "details": {
                    "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
                    "received_size_bytes": len(content),
                },
            },
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4()}{suffix}"
    stored_path = upload_dir / stored_name

    stored_path.write_bytes(content)

    checksum = hashlib.sha256(content).hexdigest()

    return StoredFileData(
        original_name=original_name,
        stored_name=stored_name,
        stored_path=str(stored_path),
        mime_type=received_mime_type,
        extension=suffix,
        size_bytes=len(content),
        checksum=checksum,
    )