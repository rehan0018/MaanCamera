"""Application configuration management via Pydantic BaseSettings."""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    CSRF_COOKIE_NAME: str = "mc_csrf"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    TRUSTED_PROXY_IPS: list[str] = ["127.0.0.1", "::1"]
    AUTH_LOCKOUT_MAX_ATTEMPTS: int = 5
    AUTH_LOCKOUT_BASE_MINUTES: int = 5
    REQUIRE_ADMIN_TOTP: bool = False
    TERMS_VERSION: str = "2026-11-27"
    PRIVACY_VERSION: str = "2026-11-27"

    # Rate Limiting (Valkey-backed via slowapi)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str | None = None

    # Upload Limits
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Database (DATABASE_URL uses non-owner app role in Postgres; SYNC_DATABASE_URL uses owner role for Alembic)
    APP_DB_USER: str = "maancamera_app"
    APP_DB_PASSWORD: str = "maancamera_app_dev_password"
    DATABASE_URL: str = "postgresql+asyncpg://maancamera:maancamera_local_dev_password@localhost:5432/maancamera_db"
    SYNC_DATABASE_URL: str = "postgresql://maancamera:maancamera_local_dev_password@localhost:5432/maancamera_db"

    # Notifications / Email & OTP (optional SMTP host; falls back to safe non-secret dev sink)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@maancamera.com"
    SMTP_USE_TLS: bool = True

    # Marketplace Money Defaults (configurable pending CA / accountant sign-off)
    PLATFORM_COMMISSION_BPS: int = 1000  # 10.00%
    DEFAULT_ADVANCE_PERCENT: int = 25
    PAYOUT_HOLD_HOURS_AFTER_COMPLETION: int = 48

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
    RAZORPAY_WEBHOOK_SECRET: str = ""

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG=True is forbidden in production environment.")
            if self.SECRET_KEY.startswith("dev_") or len(self.SECRET_KEY) < 32:
                raise ValueError("Insecure default SECRET_KEY detected in production environment.")
            if self.CSRF_SECRET.startswith("dev_") or len(self.CSRF_SECRET) < 32:
                raise ValueError("Insecure default CSRF_SECRET detected in production environment.")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard CORS_ORIGINS is forbidden with credentialed sessions in production.")
            if (
                "maancamera_local_dev_password" in self.DATABASE_URL
                or "maancamera_local_dev_password" in self.SYNC_DATABASE_URL
                or "maancamera_app_dev_password" in self.DATABASE_URL
            ):
                raise ValueError("Default database credentials are forbidden in production environment.")
            if self.S3_SECRET_ACCESS_KEY == "maancamera_s3_secret_key_dev":
                raise ValueError("Default S3 secret key is forbidden in production environment.")
            if self.PAYMENT_PROVIDER == "mock":
                raise ValueError("PAYMENT_PROVIDER=mock is forbidden in production environment.")
            if self.PAYMENT_PROVIDER == "razorpay" and (
                not self.RAZORPAY_KEY_ID or not self.RAZORPAY_KEY_SECRET or not self.RAZORPAY_WEBHOOK_SECRET
            ):
                raise ValueError("Razorpay keys and webhook secret must be configured in production.")
            self.COOKIE_SECURE = True
        return self


settings = Settings()
