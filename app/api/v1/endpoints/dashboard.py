from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.permissions import REPORT_VIEW_OWN_SCOPE
from app.db.session import get_db
from app.services.access_control_service import is_admin
from app.services.dashboard_service import get_dashboard_summary, get_recent_activities


router = APIRouter()


@router.get("/summary")
def read_dashboard_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_VIEW_OWN_SCOPE)),
):
    lecturer_id = None if is_admin(current_user) else current_user.id
    return get_dashboard_summary(db=db, lecturer_id=lecturer_id)


@router.get("/recent-activities")
def read_recent_activities(
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_VIEW_OWN_SCOPE)),
):
    lecturer_id = None if is_admin(current_user) else current_user.id
    return get_recent_activities(db=db, lecturer_id=lecturer_id)
