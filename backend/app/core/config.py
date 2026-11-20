from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql+psycopg://wedding:wedding@localhost:5432/wedding"
    admin_password: str = "change-me"
    jwt_secret: str = "change-me-too"
    jwt_expire_minutes: int = 60 * 12
    # Comma-separated list, e.g. "http://localhost:3000,https://our-wedding.com"
    cors_origins: str = "http://localhost:3000"
    invite_lookup_rate_limit: str = "10/minute"
    staff_login_rate_limit: str = "10/minute"
    # Public frontend address, used to build invitation links (SITE_URL/invite/<token>).
    site_url: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def use_psycopg3_driver(cls, v: str) -> str:
        # Neon / most providers hand out "postgresql://" or "postgres://" URLs.
        # SQLAlchemy needs the driver spelled out to pick psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    def invite_url(self, token: str) -> str:
        return f"{self.site_url.rstrip('/')}/invite/{token}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
