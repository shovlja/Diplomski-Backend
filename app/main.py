# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, asyncio, time

from sqlalchemy import text  # 👈 ping upit

load_dotenv()

from app.core.config import settings
from app.db.database import Base, engine
from app.api.routes import auth_router
from app.api.routes import users as users_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

origins_raw = os.getenv("FRONTEND_URL", settings.frontend_url)
origins = [o.strip() for o in str(origins_raw).split(",") if o.strip()] or ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router.router)

async def wait_for_db(engine, timeout: float = 60.0, interval: float = 1.0):
    """Čeka da se DB podigne; radi i u docker-compose i lokalno."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as e:
            last_error = e
            await asyncio.sleep(interval)
    raise RuntimeError(f"Database not ready after {timeout}s") from last_error

@app.on_event("startup")
async def on_startup():
    # sačekaj spremnost baze pa tek onda kreiraj šemu
    await wait_for_db(engine, timeout=60.0)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}
