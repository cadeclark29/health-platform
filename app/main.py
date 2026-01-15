from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.db.database import engine, Base
from app.api import users, dispenser, integrations


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

# Serve static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    return FileResponse(static_path / "index.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
