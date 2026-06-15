from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.job_schema import JobRead
from app.services.job_service import get_job_by_id


router = APIRouter()


@router.get("/{job_id}", response_model=JobRead)
def read_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = get_job_by_id(
        db=db,
        job_id=job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": "Không tìm thấy job xử lý.",
                "details": {
                    "job_id": str(job_id),
                },
            },
        )

    return job