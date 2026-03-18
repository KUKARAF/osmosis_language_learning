from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app import plugins
from app.llm.prompt_loader import registry as prompt_registry

# Load plugins at import time so routers can be registered at module level
# (include_router must not be called inside the lifespan — FastAPI will
# recursively merge lifespans and crash)
_plugins = plugins.load_plugins()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Register core prompts first (lowest priority)
    prompt_registry.register_dir(Path(__file__).parent / "prompts")

    # Register plugin prompts (higher priority than core) and run startup hooks
    for plugin in _plugins:
        get_pd = getattr(plugin, "get_prompts_dir", None)
        if get_pd and (prompts_dir := get_pd()):
            prompt_registry.register_dir(prompts_dir)
        await plugin.on_startup(app)

    yield


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
    version,
)

app = FastAPI(title="osmosis", version=version._resolve_version(), lifespan=lifespan)

# --- built-in routers ---

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
app.include_router(version.router, prefix="/api/version", tags=["version"])

# --- plugin routers (included at module level, not inside lifespan) ---
for _plugin in _plugins:
    get_r = getattr(_plugin, "get_router", None)
    if get_r and (_router := get_r()):
        app.include_router(
            _router,
            prefix=f"/api/plugins/{_plugin.name}",
            tags=[f"plugin:{_plugin.name}"],
        )

# --- static frontend (must be last so it doesn't shadow /api) ---
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
