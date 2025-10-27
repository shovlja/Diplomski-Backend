from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, asyncio, time
from sqlalchemy import text

load_dotenv()

from app.core.config import settings
from app.db.database import Base, engine
from app.api.routes import auth_router
from app.api.routes import users as users_router
from app.api.routes import teams as teams_router
from app.api.routes import notifications as notifications_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

origins_raw = os.getenv("FRONTEND_URL", settings.frontend_url)
origins = [o.strip().rstrip("/") for o in str(origins_raw).split(",") if o.strip()]

# Dev defaulti – obavezno tačan origin bez završne /
defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
for o in defaults:
    if o not in origins:
        origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router.router)
app.include_router(teams_router.router)
app.include_router(notifications_router.router)


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
    # VAŽNO: importuj sve modele PRE create_all, da Notification završi u metadata
    from app.models import user, team, invitation, notification  # noqa: F401
    await wait_for_db(engine, timeout=60.0)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}
