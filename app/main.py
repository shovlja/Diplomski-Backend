from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from dotenv import load_dotenv
import os

# from app.api.routes import users, boards, lists, cards, comments, labels, invitations, activity_logs, notifications
# from app.db.database import engine, Base

# Base.metadata.create_all(bind=engine)

load_dotenv()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# app.include_router(users.router, prefix="/users", tags=["Users"])
# app.include_router(boards.router, prefix="/boards", tags=["Boards"])
# app.include_router(lists.router, prefix="/lists", tags=["Lists"])
# app.include_router(cards.router, prefix="/cards", tags=["Cards"])
# app.include_router(comments.router, prefix="/comments", tags=["Comments"])
# app.include_router(labels.router, prefix="/labels", tags=["Labels"])
# app.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
# app.include_router(activity_logs.router, prefix="/activity-logs", tags=["Activity Logs"])
# app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.app_name}"}
