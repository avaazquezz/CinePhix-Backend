"""CinePhix Backend - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.redis import close_redis
from app.routers import review_comments_router, activity_v2_router, follows_v2_router
from app.routers import auth_router, users_router, watchlist_router, favorites_router, tmdb_router, reviews_router, follows_router, user_stats_router, lists_router, activity_router, notifications_router, ai_router, payments_router, trakt_router, discover_router, watched_router, list_comments_router, list_collaborators_router
from app.services.notification_service import manager


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

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

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
app.include_router(notifications_router)
app.include_router(ai_router)
app.include_router(payments_router)
app.include_router(trakt_router)
app.include_router(discover_router)
app.include_router(watched_router)
app.include_router(list_comments_router)
app.include_router(list_collaborators_router)
app.include_router(review_comments_router)
app.include_router(activity_v2_router)
app.include_router(follows_v2_router)


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


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time notifications.
    Client must provide a valid JWT access token as query param 'token'.
    Connection is per-user; multiple tabs share the same user_id.
    """
    # Validate token
    from app.services.auth_service import verify_access_token
    payload = verify_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = str(payload.get("sub"))
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep alive — receive any ping from client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
