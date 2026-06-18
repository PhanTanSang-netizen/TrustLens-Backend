import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api_router import api_router


def parse_cors_origins() -> list[str]:
    cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,https://frontend-trust-lens-fkk2-ar6xkjd7w.vercel.app",
    )

    return [
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ]


app = FastAPI(
    title="TrustLens API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api/v1"
)


@app.get("/")
def read_root():
    return {
        "message": "TrustLens Backend API is running.",
        "docs": "/docs",
        "api": "/api/v1",
    }