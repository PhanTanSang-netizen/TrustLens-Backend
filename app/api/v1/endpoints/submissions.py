from pathlib import Path
from uuid import uuid4
from hashlib import sha256

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status


router = APIRouter()

UPLOAD_DIR = Path("uploads")

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload")
async def upload_submission_file(
    file: UploadFile = File(...),
    assignment_id: str = Form(...),
    owner_label: str | None = Form(default=None),
):
    original_name = file.filename or ""
    file_extension = Path(original_name).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error_code": "FILE_UNSUPPORTED_TYPE",
                "message": "Chỉ hỗ trợ file PDF hoặc DOCX.",
                "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
            },
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error_code": "FILE_UNSUPPORTED_MIME_TYPE",
                "message": "MIME type của file không hợp lệ.",
                "received_type": file.content_type,
            },
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_EMPTY",
                "message": "File rỗng, không thể upload.",
            },
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": f"File vượt quá giới hạn {MAX_FILE_SIZE_MB}MB.",
            },
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())
    submission_id = str(uuid4())
    job_id = str(uuid4())

    stored_name = f"{file_id}{file_extension}"
    stored_path = UPLOAD_DIR / stored_name

    checksum = sha256(file_bytes).hexdigest()
    stored_path.write_bytes(file_bytes)

    return {
        "message": "Upload file thành công.",
        "submission": {
            "submission_id": submission_id,
            "assignment_id": assignment_id,
            "owner_label": owner_label,
            "status": "UPLOADED",
        },
        "file": {
            "file_id": file_id,
            "original_name": original_name,
            "stored_name": stored_name,
            "stored_path": str(stored_path),
            "mime_type": file.content_type,
            "size_bytes": len(file_bytes),
            "checksum": checksum,
        },
        "job": {
            "job_id": job_id,
            "status": "QUEUED",
            "progress": 0,
            "step": "queued",
            "error_code": None,
        },
        "note": "Dev version: dữ liệu chưa lưu PostgreSQL. Bước tiếp theo sẽ lưu files, submissions và processing_jobs.",
    }