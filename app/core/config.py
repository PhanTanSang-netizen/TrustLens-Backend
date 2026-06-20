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

    TRUST_SCORE_VERSION: str = "trust-score-v1.2"

    RELEVANCE_PROVIDER: str = "gemini"
    RELEVANCE_FALLBACK_PROVIDER: str = "local"
    RELEVANCE_PROMPT_VERSION: str = "c4-v2"
    RELEVANCE_THRESHOLD_PROFILE: str = "gemini-embedding-2-768-c4-v2"

    GEMINI_API_KEY: str | None = None
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    GEMINI_EMBEDDING_DIMENSION: int = 768
    GEMINI_TIMEOUT_SECONDS: int = 15
    GEMINI_MAX_RETRIES: int = 2

    LOCAL_EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    LOCAL_EMBEDDING_DEVICE: str = "cpu"

    HF_TOKEN: str | None = None
    HF_EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"

    OPENALEX_API_KEY: str | None = None
    CROSSREF_MAILTO: str = "team-email@example.edu"

    AI_DATA_MODE: str = "sanitized_text_only"
    AI_PERSIST_RAW_INPUT: bool = False
    AI_LOG_INPUT_TEXT: bool = False

    FEATURE_C4_V2: bool = False
    FEATURE_DOI_CONFLICT_V2: bool = False
    FEATURE_RETRACTION_V2: bool = False
    FEATURE_WEIGHT_INVARIANCE_V2: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
