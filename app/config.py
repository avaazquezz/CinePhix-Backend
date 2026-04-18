"""Application configuration from environment variables."""

import json
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
_DEFAULT_CORS_ORIGINS_STR = ",".join(_DEFAULT_CORS_ORIGINS)


def _parse_cors_origins(value: Any) -> list[str]:
    """Accept JSON array, comma-separated URLs, or empty (use defaults)."""
    if value is None:
        return list(_DEFAULT_CORS_ORIGINS)
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return list(_DEFAULT_CORS_ORIGINS)
        if s.startswith("["):
            parsed = json.loads(s)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS as JSON must be an array of strings")
            return [str(x).strip() for x in parsed if str(x).strip()]
        return [part.strip() for part in s.split(",") if part.strip()]
    raise TypeError("cors_origins must be a list or string")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "CinePhix API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cinephix"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "changeme-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # TMDB
    tmdb_api_key: str = "e546f0210838c597382ddcad9f8e0647"
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p"

    # Email (Resend - free tier)
    resend_api_key: str = ""
    email_from: str = "CinePhix <noreply@cinephix.com>"

    # Groq AI
    groq_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    frontend_url: str = "http://localhost:3000"

    # OAuth Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Stored as str so pydantic-settings does not JSON-decode .env values (comma-separated is common).
    cors_origins_raw: str = Field(
        default=_DEFAULT_CORS_ORIGINS_STR,
        validation_alias="CORS_ORIGINS",
    )

    # Rate limiting
    rate_limit_public: str = "100/minute"
    rate_limit_authenticated: str = "1000/minute"

    @property
    def cors_origins(self) -> list[str]:
        """Origins for CORSMiddleware: comma-separated or JSON array in CORS_ORIGINS."""
        return _parse_cors_origins(self.cors_origins_raw)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
