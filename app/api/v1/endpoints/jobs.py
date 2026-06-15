from fastapi import APIRouter


router = APIRouter()


@router.get("/{job_id}")
def get_job_status(job_id: str):
    return {
        "job_id": job_id,
        "status": "QUEUED",
        "progress": 0,
        "step": "queued",
        "error_code": None,
        "message": "Job đã được tạo. Worker thật sẽ được triển khai ở bước sau.",
    }