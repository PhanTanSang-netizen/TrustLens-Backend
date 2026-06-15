from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.user_schema import UserRead


router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user=Depends(get_current_user),
):
    return current_user