# tests/conftest.py
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from sqlalchemy import text

# Opciona test baza: export TEST_DATABASE_URL da pregazi produkcioni DATABASE_URL
test_db_url = os.getenv("TEST_DATABASE_URL")
if test_db_url:
    os.environ["DATABASE_URL"] = test_db_url

from app.main import app
from app.db.database import engine, Base


@pytest_asyncio.fixture(scope="function")
async def app_lifespan():
    """
    Pokreće FastAPI startup/shutdown jednom za trajanje sesije testova.
    (Ne koristi zaseban httpx lifespan param – ovo je kanonski način.)
    """
    async with LifespanManager(app):
        yield


@pytest_asyncio.fixture
async def async_client(app_lifespan):
    """
    httpx.AsyncClient preko ASGITransport-a. Lifespan je već aktiviran gore.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """
    Pre svakog testa napravi šemu (idempotentno) i očisti tabele,
    a posle svakog testa zatvori pool (dispose) da ne vučemo konekcije u novi loop.
    """
    # --- setup ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Dodaj i ostale tabele kad ih uvedeš
        await conn.execute(text("TRUNCATE TABLE users CASCADE"))

    yield

    # --- teardown: ubij pool konekcija da sledeći test kreće sa čistim loop-om ---
    await engine.dispose()
