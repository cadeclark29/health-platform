from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.db.database import engine, Base
from app.api import users, dispenser, integrations, upload, checkins, interactions, mixes
from app.api.mixes import blends_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Health Platform API",
    description="AI-powered supplement recommendation engine",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(dispenser.router, prefix="/dispense", tags=["dispenser"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(checkins.router, prefix="/checkins", tags=["checkins"])
app.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
app.include_router(blends_router, prefix="/mixes/blends", tags=["blends"])  # Must be before mixes router
app.include_router(mixes.router, prefix="/mixes", tags=["mixes"])

# Serve static files
static_path = Path(__file__).resolve().parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Health Platform API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/debug/config")
async def debug_config():
    from app.config import get_settings
    settings = get_settings()
    return {
        "openai_key_set": bool(settings.openai_api_key),
        "openai_key_prefix": settings.openai_api_key[:10] + "..." if settings.openai_api_key else None,
        "openai_key_length": len(settings.openai_api_key) if settings.openai_api_key else 0
    }


@app.get("/debug/openai-test")
async def debug_openai_test():
    from app.engine.llm import llm_personalizer

    result = {
        "client_exists": llm_personalizer.client is not None,
    }

    if llm_personalizer.client:
        try:
            response = await llm_personalizer.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10
            )
            result["api_works"] = True
            result["response"] = response.choices[0].message.content
        except Exception as e:
            result["api_works"] = False
            result["error"] = str(e)

    return result
