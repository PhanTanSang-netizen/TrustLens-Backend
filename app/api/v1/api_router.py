from fastapi import APIRouter

from app.api.v1.endpoints import auth, assignments, classes, courses, health, jobs, submissions, users


api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["Courses"],
)

api_router.include_router(
    classes.router,
    prefix="/classes",
    tags=["Classes"],
)

api_router.include_router(
    assignments.router,
    prefix="/assignments",
    tags=["Assignments"],
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