"""API routers."""

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.watchlist import router as watchlist_router
from app.routers.favorites import router as favorites_router
from app.routers.tmdb import router as tmdb_router
from app.routers.reviews import router as reviews_router
from app.routers.follows import router as follows_router
from app.routers.user_stats import router as user_stats_router
from app.routers.lists import router as lists_router
from app.routers.activity import router as activity_router
from app.routers.notifications import router as notifications_router
from app.routers.ai import router as ai_router

__all__ = [
    "auth_router",
    "users_router",
    "watchlist_router",
    "favorites_router",
    "tmdb_router",
    "reviews_router",
    "follows_router",
    "user_stats_router",
    "lists_router",
    "activity_router",
    "notifications_router",
    "ai_router",
]
