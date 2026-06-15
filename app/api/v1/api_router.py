from fastapi import APIRouter

from app.api.v1.endpoints import health, submissions, jobs


api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

api_router.include_router(
    submissions.router,
    prefix="/submissions",
    tags=["Submissions"],
)

api_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["Jobs"],
)