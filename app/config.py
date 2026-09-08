"""Application settings loaded from environment variables (or a local .env file).

All Kalshi credentials and connection strings live here instead of being
hardcoded anywhere in the codebase. Copy .env.example to .env and fill in
real values for local development; in Docker/CI, values come from the
environment / env_file directly.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Kalshi API credentials
    kalshi_key_id: str = "your-key-id-here"
    kalshi_private_key_path: Optional[str] = "./secrets/kalshi-key.key"
    kalshi_private_key_pem: Optional[str] = None
    kalshi_base_url: str = "https://demo-api.kalshi.co"

    # Postgres
    database_url: str = "postgresql+psycopg2://kalshi:kalshi@postgres:5432/kalshi"

    # Data lake
    data_lake_root: str = "./data_lake"

    # ETL: safety cap on how many pages to pull per resource per run (Kalshi's
    # demo environment can have a very large backlog of historical
    # events/markets; without a cap a full sync could take a long time and
    # give no visible progress).
    etl_max_pages: int = 20

    # Operator dashboard / session auth (demo-grade: a single seeded
    # username+password from env, compared in constant time, behind a signed
    # session cookie -- a real deployment would sit this behind an
    # OAuth2/OIDC identity provider instead).
    dashboard_username: str = "admin"
    dashboard_password: str = "changeme"
    session_secret_key: str = "dev-secret-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
