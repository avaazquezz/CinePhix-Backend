"""CinePhix Backend - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.redis import close_redis
from app.routers import auth_router, users_router, watchlist_router, favorites_router, tmdb_router, reviews_router, follows_router, user_stats_router, lists_router, activity_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for CinePhix SaaS - Auth, Watchlist, Favorites, and TMDB integration",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(watchlist_router)
app.include_router(favorites_router)
app.include_router(tmdb_router)
app.include_router(reviews_router)
app.include_router(follows_router)
app.include_router(user_stats_router)
app.include_router(lists_router)
app.include_router(activity_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }