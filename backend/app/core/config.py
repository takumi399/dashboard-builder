from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    APP_NAME: str = "Dashboard Builder API"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./dashboard.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENABLE_RATE_LIMIT: bool = True
    DATASOURCE_ENCRYPTION_KEY: str = ""
    SQL_ALLOWED_HOSTS: str = ""
    SQL_QUERY_TIMEOUT_SECONDS: int = 10
    SQL_MAX_ROWS: int = 1000
    SQLITE_DATA_DIR: str = "./data"

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

    @model_validator(mode="after")
    def validate_security_settings(self):
        if not 1 <= self.SQL_QUERY_TIMEOUT_SECONDS <= 60:
            raise ValueError("SQL_QUERY_TIMEOUT_SECONDS must be between 1 and 60")
        if not 1 <= self.SQL_MAX_ROWS <= 10000:
            raise ValueError("SQL_MAX_ROWS must be between 1 and 10000")
        if not self.DEBUG and not self.DATASOURCE_ENCRYPTION_KEY:
            raise ValueError(
                "DATASOURCE_ENCRYPTION_KEY is required when DEBUG=False"
            )
        if not self.DEBUG and self.DATASOURCE_ENCRYPTION_KEY:
            from app.services.credential_cipher import CredentialCipher

            CredentialCipher(self.DATASOURCE_ENCRYPTION_KEY)
        return self

settings = Settings()
