"""API routers."""

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.watchlist import router as watchlist_router
from app.routers.favorites import router as favorites_router
from app.routers.tmdb import router as tmdb_router

__all__ = ["auth_router", "users_router", "watchlist_router", "favorites_router", "tmdb_router"]