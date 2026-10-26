from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # OPENAI_API_KEY / AGENT_LLM_* for the agent layer

from backend.app.config import get_settings
from backend.app.database import init_db
from backend.app.routers import tickets


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # Warm the agent graph so the first ticket is not slow
    try:
        from backend.app.agents_bridge import get_agent_service

        svc = get_agent_service()
        provider = svc.settings.llm_provider
        print(f"[agents] LLM provider={provider!r} model={svc.settings.llm_model!r} active={svc.llm is not None}")
    except Exception as exc:
        # Agents optional at boot; routes still serve persistence
        print(f"[agents] warmup skipped: {exc}")
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
    from backend.app.agents_bridge import get_agent_service

    try:
        svc = get_agent_service()
        llm_info = {
            "provider": svc.settings.llm_provider,
            "model": svc.settings.llm_model,
            "llm_active": svc.llm is not None,
        }
    except Exception as exc:
        llm_info = {"error": str(exc)}
    return {"status": "ok", "app": settings.app_name, "agents": llm_info}