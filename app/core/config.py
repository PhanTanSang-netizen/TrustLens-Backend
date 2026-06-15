from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TrustLens API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str

    SECRET_KEY: str = "trustlens-dev-secret-change-later"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()