"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Corporate CMS Engine"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cms"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production-very-secret-key")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS - stored as comma-separated string in env
    # Common frontend dev ports: 3000 (Next.js), 3001, 5173 (Vite), 8080, 5174
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:5174,http://localhost:8080",
        alias="cors_origins"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    # S3 Storage (auto-configured to MinIO in development)
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_name: str = "cms-assets"
    s3_region: str = "us-east-1"

    @model_validator(mode='after')
    def set_development_s3_defaults(self) -> "Settings":
        """Auto-configure MinIO for development if S3 not explicitly set.
        
        In development mode, if S3 credentials are not provided,
        automatically use local MinIO defaults (localhost:9000).
        In production, explicit configuration is required.
        """
        if self.environment == "development":
            if not self.s3_access_key:
                object.__setattr__(self, 's3_access_key', 'minioadmin')
            if not self.s3_secret_key:
                object.__setattr__(self, 's3_secret_key', 'minioadmin')
            if not self.s3_endpoint_url:
                object.__setattr__(self, 's3_endpoint_url', 'http://localhost:9000')
        return self

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_login_requests: int = 20  # Increased from 5 for development
    rate_limit_login_window_seconds: int = 60  # Reduced from 300 (5 min) to 60 (1 min)
    rate_limit_inquiry_requests: int = 3
    rate_limit_inquiry_window_seconds: int = 60

    # Email (SendGrid/Mailgun)
    email_provider: Literal["sendgrid", "mailgun", "smtp", "console"] = "console"
    email_api_key: str = ""
    email_from_address: str = "noreply@example.com"
    email_from_name: str = "Corporate CMS"

    # Telegram (legacy - global bot for simple notifications)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Encryption (for securing sensitive data like API tokens)
    # Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
    encryption_key: str = ""

    # Public API URL (for webhook URLs, must be HTTPS in production)
    public_api_url: str = ""

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Single-tenant mode settings
    # When single_tenant_mode=True, the system automatically uses the default tenant
    # without requiring X-Tenant-ID header on login
    single_tenant_mode: bool = True
    default_tenant_slug: str = "main"
    default_tenant_name: str = "Main Site"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

