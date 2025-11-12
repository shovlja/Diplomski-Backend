from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, asyncio, time
from sqlalchemy import text

load_dotenv()

from app.core.config import settings
from app.db.database import Base, engine

# postojeći routers
from app.api.routes import auth_router
from app.api.routes import users as users_router
from app.api.routes import teams as teams_router
from app.api.routes import notifications as notifications_router
from app.api.routes import boards as boards_router

# kanban routers (lists/cards/labels/comments/checklists)
from app.api.routes import kanban_lists as kanban_lists_router
from app.api.routes import kanban_cards as kanban_cards_router
from app.api.routes import kanban_labels as kanban_labels_router
from app.api.routes import board_labels as board_labels_router
from app.api.routes import kanban_comments as kanban_comments_router
from app.api.routes import kanban_checklists as kanban_checklists_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

# CORS
origins_raw = os.getenv("FRONTEND_URL", settings.frontend_url)
origins = [o.strip().rstrip("/") for o in str(origins_raw).split(",") if o.strip()]
for o in ["http://localhost:5173", "http://127.0.0.1:5173"]:
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

# include routers
app.include_router(auth_router)
app.include_router(users_router.router)
app.include_router(teams_router.router)
app.include_router(notifications_router.router)
app.include_router(boards_router.router)

# lists
app.include_router(kanban_lists_router.router)   # /api/v1/lists (PATCH/DELETE)
app.include_router(kanban_lists_router.bridge)   # /api/v1/boards/{id}/lists (+reorder)

# cards
app.include_router(kanban_cards_router.router)   # /api/v1/cards (PATCH + labels/comments/members)
app.include_router(kanban_cards_router.bridge)   # /api/v1/lists/{id}/cards (+reorder)

# labels
app.include_router(kanban_labels_router.router)  # /api/v1/labels (GET/PATCH/DELETE)
app.include_router(kanban_labels_router.bridge)
app.include_router(board_labels_router.router)  # /api/v1/boards/{id}/labels (POST)

# checklists + comments
app.include_router(kanban_checklists_router.router)  # /api/v1/cards/{id}/checklists, /api/v1/checklists...
app.include_router(kanban_comments_router.router)    # /api/v1/comments (ako koristiš i ove rute)

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
    # VAŽNO: importuj SVE modele pre create_all, da bi tabele ušle u metadata
    from app.models import (
        user, team, invitation, notification,            # postojeće
        board, board_list, board_card,                   # board core
        board_checklist, board_label, board_comment      # board dodatno
    )  # noqa: F401

    await wait_for_db(engine, timeout=60.0)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}
