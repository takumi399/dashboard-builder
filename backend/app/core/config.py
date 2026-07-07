from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    APP_NAME: str = "Dashboard Builder API"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./dashboard.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENABLE_RATE_LIMIT: bool = True

    # PostgreSQL convenience environment variables
    # If POSTGRES_HOST is set, these are used to build DATABASE_URL
    # unless DATABASE_URL is explicitly overridden via environment variable.
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = ""
    POSTGRES_DB: str = ""

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def build_postgres_url(self):
        """If PostgreSQL env vars are provided and DATABASE_URL is still the default SQLite, build the PG URL."""
        if self.POSTGRES_HOST and self.DATABASE_URL.startswith("sqlite"):
            db_name = self.POSTGRES_DB or self.POSTGRES_USER or "dashboard"
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:5432/{db_name}"
            )
        return self

settings = Settings()
