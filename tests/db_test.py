import pytest
import asyncio
from sqlalchemy import text
from app.db.database import engine, get_db
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_db_connection():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

@pytest.mark.asyncio
async def test_session_dependency():
    # Test da li get_db vraća AsyncSession
    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    await gen.aclose()
