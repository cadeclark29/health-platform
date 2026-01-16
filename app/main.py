from pathlib import Path

from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import engine, Base
from app.db import get_db
from app.api import users, dispenser, integrations, upload, checkins, interactions, mixes
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


@app.get("/debug/oura/{user_id}")
def debug_oura_token(user_id: str, db: Session = Depends(get_db)):
    """Debug endpoint to check Oura token status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    return {
        "has_token": user.oura_token is not None,
        "token_type": type(user.oura_token).__name__ if user.oura_token else None,
        "token_keys": list(user.oura_token.keys()) if user.oura_token and isinstance(user.oura_token, dict) else None,
    }


@app.post("/debug/oura/{user_id}/set-test-token")
def set_test_token(user_id: str, db: Session = Depends(get_db)):
    """Test if we can save a token to the database."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    test_token = {"access_token": "test123", "token_type": "Bearer", "expires_in": 3600}
    user.oura_token = test_token
    db.commit()
    db.refresh(user)

    return {
        "saved": user.oura_token is not None,
        "matches": user.oura_token == test_token if user.oura_token else False
    }


@app.get("/api/oura/callback-test")
async def oura_callback_test(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Test callback that returns JSON instead of redirecting."""
    user_id = state
    if not user_id:
        return {"error": "missing_user_id"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "user_not_found"}

    oura = OuraIntegration()
    redirect_uri = "https://health-platform-production-94aa.up.railway.app/api/oura/callback"

    try:
        token = await oura.exchange_code(code, redirect_uri)
        user.oura_token = token
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "token_saved": user.oura_token is not None,
            "token_keys": list(token.keys()) if token else None
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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
    print(f"[OURA CALLBACK] code={code[:20]}..., state={state}, error={error}")

    if error:
        print(f"[OURA CALLBACK] OAuth error from Oura: {error}")
        return RedirectResponse(url=f"/?oura_error={error}")

    user_id = state
    if not user_id:
        print("[OURA CALLBACK] Missing user_id in state")
        return RedirectResponse(url="/?oura_error=missing_user_id")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"[OURA CALLBACK] User not found: {user_id}")
        return RedirectResponse(url="/?oura_error=user_not_found")

    oura = OuraIntegration()
    redirect_uri = "https://health-platform-production-94aa.up.railway.app/api/oura/callback"

    try:
        print(f"[OURA CALLBACK] Exchanging code for token...")
        token = await oura.exchange_code(code, redirect_uri)
        print(f"[OURA CALLBACK] Got token: {bool(token)}, has access_token: {'access_token' in token if token else False}")
        print(f"[OURA CALLBACK] Token keys: {list(token.keys()) if token else 'None'}")

        # Save token
        user.oura_token = token
        print(f"[OURA CALLBACK] Set user.oura_token, about to commit...")
        db.commit()
        print(f"[OURA CALLBACK] Committed!")
        db.refresh(user)
        print(f"[OURA CALLBACK] After refresh, user.oura_token is not None: {user.oura_token is not None}")

        # Double-check by re-querying
        check_user = db.query(User).filter(User.id == user_id).first()
        print(f"[OURA CALLBACK] Re-queried user, oura_token is not None: {check_user.oura_token is not None}")

        return RedirectResponse(url="/?oura_connected=true")
    except Exception as e:
        print(f"[OURA CALLBACK] Exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Clean error message for URL - remove newlines and special chars
        error_msg = str(e).split('\n')[0][:80]
        from urllib.parse import quote
        return RedirectResponse(url=f"/?oura_error={quote(error_msg)}")


