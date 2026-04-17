"""SQLAlchemy models for CinePhix."""

from app.models.user import User, UserPreferences, RefreshToken, MagicLink
from app.models.watchlist import WatchlistItem
from app.models.favorite import Favorite
from app.models.review import Review
from app.models.review_vote import ReviewVote, VoteType
from app.models.user_stats import UserStats
from app.models.follow import UserFollow

__all__ = [
    "User",
    "UserPreferences",
    "RefreshToken",
    "MagicLink",
    "WatchlistItem",
    "Favorite",
    "Review",
    "ReviewVote",
    "VoteType",
    "UserStats",
    "UserFollow",
]
