from pathlib import Path

from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import engine, Base
from app.db import get_db
from app.api import users, dispenser, integrations, upload, checkins, interactions, mixes, analytics
from app.api.mixes import blends_router
from app.models import User
from app.integrations import OuraIntegration


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
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

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




@app.get("/privacy")
async def privacy_policy():
    privacy_file = static_path / "privacy.html"
    if privacy_file.exists():
        return FileResponse(privacy_file)
    return {"error": "Privacy policy not found"}


@app.get("/terms")
async def terms_of_service():
    terms_file = static_path / "terms.html"
    if terms_file.exists():
        return FileResponse(terms_file)
    return {"error": "Terms of service not found"}


# --- Oura OAuth Routes (at /api/oura/*) ---

@app.get("/api/oura/auth")
def start_oura_auth(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Start Oura OAuth flow.
    Redirects user to Oura authorization page.
    """
    from app.config import get_settings
    settings = get_settings()

    if not settings.oura_client_id or not settings.oura_client_secret:
        return {"error": "Oura API credentials not configured"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    oura = OuraIntegration()
    redirect_uri = "https://health-platform-production-94aa.up.railway.app/api/oura/callback"
    auth_url = oura.get_auth_url(redirect_uri, state=user_id)

    return RedirectResponse(url=auth_url)


@app.get("/api/oura/callback")
async def oura_oauth_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Oura OAuth callback.
    The state parameter contains the user_id.
    """
    if error:
        return RedirectResponse(url=f"/?oura_error={error}")

    user_id = state
    if not user_id:
        return RedirectResponse(url="/?oura_error=missing_user_id")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/?oura_error=user_not_found")

    oura = OuraIntegration()
    redirect_uri = "https://health-platform-production-94aa.up.railway.app/api/oura/callback"

    try:
        token = await oura.exchange_code(code, redirect_uri)
        user.oura_token = token
        db.commit()
        return RedirectResponse(url="/?oura_connected=true")
    except Exception as e:
        from urllib.parse import quote
        error_msg = str(e).split('\n')[0][:80]
        return RedirectResponse(url=f"/?oura_error={quote(error_msg)}")


@app.get("/api/migrate")
def run_migrations(db: Session = Depends(get_db)):
    """
    Run database migrations to add new columns.
    Safe to run multiple times - uses IF NOT EXISTS.
    """
    from sqlalchemy import text

    migrations = [
        # Add new columns to supplement_starts table
        "ALTER TABLE supplement_starts ADD COLUMN IF NOT EXISTS supplement_name VARCHAR",
        "ALTER TABLE supplement_starts ADD COLUMN IF NOT EXISTS is_manual BOOLEAN DEFAULT FALSE",
        "ALTER TABLE supplement_starts ADD COLUMN IF NOT EXISTS dosage VARCHAR",
        "ALTER TABLE supplement_starts ADD COLUMN IF NOT EXISTS frequency VARCHAR",
        "ALTER TABLE supplement_starts ADD COLUMN IF NOT EXISTS reason VARCHAR",
        # Add new columns to users table for onboarding
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS health_goal VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_complete VARCHAR",
        # Push notification fields
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS push_subscription JSONB",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{}'",
    ]

    results = []
    for migration in migrations:
        try:
            db.execute(text(migration))
            db.commit()
            results.append({"sql": migration[:50] + "...", "status": "success"})
        except Exception as e:
            results.append({"sql": migration[:50] + "...", "status": "error", "error": str(e)})

    return {"migrations": results}


