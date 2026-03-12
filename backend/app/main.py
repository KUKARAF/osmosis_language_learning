from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="osmosis", version="0.1.0", lifespan=lifespan)

# --- routers (mounted after they exist) ---
from app.routers import (  # noqa: E402
    auth,
    billing,
    cats,
    chat,
    communes,
    goals,
    notifications,
    srs,
    users,
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(cats.router, prefix="/api/cats", tags=["cats"])
app.include_router(srs.router, prefix="/api/srs", tags=["srs"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(
    notifications.router, prefix="/api/notifications", tags=["notifications"]
)
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(communes.router, prefix="/api/communes", tags=["communes"])

# --- static frontend (must be last so it doesn't shadow /api) ---
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
