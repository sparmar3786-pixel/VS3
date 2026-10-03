from fastapi import APIRouter
from backend.config import get_settings

router = APIRouter(prefix="/api/platform", tags=["platform"])

@router.get("/status")
async def status():
    s = get_settings()
    return {
        "edge": "cloudflare-worker",
        "database": "supabase-postgres" if s.supabase_enabled else "sqlite-fallback",
        "memory": "hybrid",
        "ai_layers": 6,
        "live_orders": False,
        "angel_credentials_server_side": True,
    }

@router.get("/free-stack")
async def free_stack():
    return {
        "frontend": "cloudflare-workers-static-assets",
        "edge": "cloudflare-workers",
        "backend": "fastapi-python",
        "database": "supabase-postgres",
        "memory": "supabase + sqlite fallback",
        "ai": ["gemini", "groq", "cerebras", "deepseek", "cloudflare-ai", "ollama"],
        "broker": "angel-one-smartapi",
        "orders": "disabled",
    }

def build_router():
    return router
