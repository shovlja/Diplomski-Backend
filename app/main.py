from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from app.api.routes import users, boards, lists, cards, comments, labels, invitations, activity_logs, notifications
# from app.db.database import engine, Base

# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PM Hub",
    description="Backend API za PM Hub projekat",
    version="1.0.0",
)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
def read_root():
    return {"message": "Welcome to PM Hub!"}
