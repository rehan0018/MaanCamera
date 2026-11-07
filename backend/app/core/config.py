"""Application configuration management via Pydantic BaseSettings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "MaanCamera"
    APP_DOMAIN: str = "localhost"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    API_V1_PREFIX: str = "/api/v1"

    # Regional & Localization (India First)
    DEFAULT_COUNTRY: str = "IN"
    DEFAULT_CURRENCY: str = "INR"
    TIMEZONE: str = "Asia/Kolkata"

    # Security
    SECRET_KEY: str = "dev_insecure_maancamera_super_secret_key_change_in_production_32b_min"
    CSRF_SECRET: str = "dev_insecure_csrf_secret_token_1234567890abcdef"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SESSION_COOKIE_NAME: str = "mc_session"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://maancamera:maancamera_local_dev_password@localhost:5432/maancamera_db"
    SYNC_DATABASE_URL: str = "postgresql://maancamera:maancamera_local_dev_password@localhost:5432/maancamera_db"

    # Valkey / Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # SeaweedFS / S3 Object Storage
    S3_ENDPOINT_URL: str = "http://localhost:8333"
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:8333"
    S3_ACCESS_KEY_ID: str = "maancamera_s3_admin"
    S3_SECRET_ACCESS_KEY: str = "maancamera_s3_secret_key_dev"
    S3_BUCKET_PUBLIC_PORTFOLIOS: str = "mc-public-portfolios"
    S3_BUCKET_PRIVATE_UPLOADS: str = "mc-private-originals"
    S3_REGION: str = "ap-south-1"

    # AI Runtime (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_FALLBACK_MODEL: str = "mistral:7b"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    CLIP_MODEL_NAME: str = "ViT-B-32"
    AI_TIMEOUT_SECONDS: int = 15
    AI_ENABLED: bool = True

    # Payments
    PAYMENT_PROVIDER: str = "mock"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""


settings = Settings()
