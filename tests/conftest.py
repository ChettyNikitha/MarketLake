"""Shared pytest fixtures.

Unit tests never touch the network or a real database. Integration test
fixtures (test Postgres engine/session) require a running Postgres reachable
via the DATABASE_URL environment variable (e.g. `docker compose up -d postgres`
locally, or the CI service container).
"""
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a sample fixture JSON file by filename (e.g. 'sample_events.json')."""
    with open(FIXTURES_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_events_json() -> dict:
    return load_fixture("sample_events.json")


@pytest.fixture
def sample_markets_json() -> dict:
    return load_fixture("sample_markets.json")


@pytest.fixture
def rsa_private_key_pem() -> str:
    """A throwaway RSA private key (PEM text) for signing tests -- never a real
    Kalshi credential.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


@pytest.fixture
def mock_kalshi_client(monkeypatch, rsa_private_key_pem):
    """A KalshiClient instance wired to a throwaway key and no real network
    calls (tests that need HTTP responses should monkeypatch `.get`/`.session`
    themselves).
    """
    from app.config import Settings
    from etl.kalshi_client import KalshiClient

    settings = Settings(
        kalshi_key_id="test-key-id",
        kalshi_private_key_pem=rsa_private_key_pem,
        kalshi_base_url="https://demo-api.kalshi.co",
        database_url="postgresql+psycopg2://kalshi:kalshi@localhost:5432/kalshi_test",
        data_lake_root="./data_lake",
    )
    return KalshiClient(settings=settings)


@pytest.fixture
def test_database_url() -> str:
    """DATABASE_URL for the integration test Postgres. Integration tests are
    skipped if this isn't reachable.
    """
    return os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://kalshi:kalshi@localhost:5432/kalshi"
    )


@pytest.fixture
def test_engine(test_database_url):
    """A SQLAlchemy engine for the integration test database. Skips the test
    if Postgres isn't reachable.
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(test_database_url, future=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Postgres not reachable at {test_database_url}: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_engine):
    from sqlalchemy.orm import sessionmaker

    session_local = sessionmaker(bind=test_engine, future=True)
    session = session_local()
    yield session
    session.close()


@pytest.fixture
def client(test_engine):
    """FastAPI TestClient with get_db overridden to use the test Postgres
    engine/session instead of the app's configured DATABASE_URL.
    """
    from sqlalchemy.orm import sessionmaker

    from app.db import get_db
    from app.main import app

    session_local = sessionmaker(bind=test_engine, future=True)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
