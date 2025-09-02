# app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

Base = declarative_base()

# Async engine (asyncpg)
engine = create_async_engine(
    settings.database_url,  # npr. postgresql+asyncpg://user:pass@host:5432/db
    echo=False,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)

# FastAPI dependency (async)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
