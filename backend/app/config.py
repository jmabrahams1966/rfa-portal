from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "RFA-2 Portal"
    environment: str = "development"
    debug: bool = False

    # Dev bypass (local testing without full auth)
    dev_auth_bypass: bool = False

    # Database (PostgreSQL)
    database_url: str  # postgresql+asyncpg://user:pass@host/dbname

    # JWT
    jwt_secret: str = "rfa-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # AWS Bedrock (Claude AI)
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    bedrock_region: str = "us-east-1"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3006",
        "http://localhost:5173",
        "https://rfa-portal.vercel.app",
        "https://rfa-portal-*.vercel.app",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
