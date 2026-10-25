from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.database import init_db
from backend.app.routers import tickets


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # Warm the agent graph so the first ticket is not slow
    try:
        from backend.app.agents_bridge import get_agent_service

        get_agent_service()
    except Exception:
        # Agents optional at boot; routes still serve persistence
        pass
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}