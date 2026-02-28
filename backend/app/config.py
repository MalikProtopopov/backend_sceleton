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

    # CORS - static fallback origins from env.
    # Dynamic origins are loaded from DB (tenant_domains + tenant_settings.site_url).
    # These env origins are ALWAYS included (for localhost dev, platform domains, etc.)
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
    s3_public_url: str = ""  # Public URL for presigned URLs (e.g., https://api.example.com/s3)
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

    @model_validator(mode='after')
    def validate_production_config(self) -> "Settings":
        """Validate critical settings for non-development environments.
        
        Ensures security-sensitive settings are properly configured
        before running in staging or production mode.
        """
        if self.environment == "development":
            return self
        
        errors: list[str] = []
        
        # JWT secret must not be default
        if self.jwt_secret_key == "change-me-in-production-very-secret-key":
            errors.append("JWT_SECRET_KEY must be changed from default in production")
        
        # JWT secret should be at least 32 characters
        if len(self.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY must be at least 32 characters in production")
        
        # S3 credentials required in production
        if not self.s3_access_key or not self.s3_secret_key:
            errors.append("S3_ACCESS_KEY and S3_SECRET_KEY are required in production")
        
        if not self.s3_endpoint_url:
            errors.append("S3_ENDPOINT_URL is required in production")
        
        # Debug must be disabled
        if self.debug:
            errors.append("DEBUG must be False in production")
        
        # CORS origins should be HTTPS in production (except localhost for testing)
        for origin in self.cors_origins:
            if origin.startswith("http://") and "localhost" not in origin:
                errors.append(f"CORS origin '{origin}' must use HTTPS in production")
        
        if errors:
            raise ValueError(
                f"Production configuration validation failed:\n" + 
                "\n".join(f"  - {e}" for e in errors)
            )
        
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

    # Sentry (error tracking — set DSN in production)
    sentry_dsn: str = ""

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Single-tenant mode settings
    # When single_tenant_mode=True, the system automatically uses the default tenant
    # without requiring X-Tenant-ID header on login.
    # Set to False for multi-tenant deployments (recommended for production).
    single_tenant_mode: bool = False
    default_tenant_slug: str = "main"
    default_tenant_name: str = "Main Site"

    # Internal endpoint shared secret (used by Caddy to call /internal/*)
    internal_secret: str = ""

    # Domain provisioning (Caddy reverse proxy)
    caddy_admin_url: str = "http://localhost:2019"
    platform_cname_target: str = "tenants.mediann.dev"
    platform_domain_suffix: str = ".mediann.dev"
    # Public IP of the platform server (used for apex-domain A-record verification).
    # Set this to the server's public IP in production.
    platform_server_ip: str = ""

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

