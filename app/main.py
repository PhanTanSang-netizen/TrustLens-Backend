import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router


CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in CORS_ORIGINS.split(",")
    if origin.strip()
]

fastapi_app = FastAPI(
    title="TrustLens API",
    version="1.0.0",
)

fastapi_app.include_router(
    api_router,
    prefix="/api/v1",
)


@fastapi_app.get("/")
def read_root():
    return {
        "message": "TrustLens Backend API is running.",
        "docs": "/docs",
        "api": "/api/v1",
    }


app = CORSMiddleware(
    fastapi_app,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
