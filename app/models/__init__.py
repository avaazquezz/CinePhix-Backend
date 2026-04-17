"""SQLAlchemy models for CinePhix."""

from app.models.user import User, UserPreferences, RefreshToken, MagicLink
from app.models.watchlist import WatchlistItem
from app.models.favorite import Favorite

__all__ = ["User", "UserPreferences", "RefreshToken", "MagicLink", "WatchlistItem", "Favorite"]