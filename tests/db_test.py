# tests/db_test.py
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, get_db

@pytest.mark.asyncio
async def test_db_connection():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

@pytest.mark.asyncio
async def test_session_dependency():
    gen = get_db()
    session = await anext(gen)  # py3.11
    try:
        assert isinstance(session, AsyncSession)
    finally:
        await gen.aclose()
