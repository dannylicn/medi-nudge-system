"""
Medi-Nudge FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.scheduler import start_scheduler, stop_scheduler
from app.routers import auth, patients, medications, escalations, prescriptions, webhook, analytics
from app.core.config import settings

# Create media storage directory
os.makedirs(settings.MEDIA_STORAGE_PATH, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Medi-Nudge API",
    description="Personalised medication adherence system for chronic disease patients in Singapore.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(medications.router)
app.include_router(escalations.router)
app.include_router(prescriptions.router)
app.include_router(webhook.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "medi-nudge-api"}
