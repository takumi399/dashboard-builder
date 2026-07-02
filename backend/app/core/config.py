from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Dashboard Builder API"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./dashboard.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
