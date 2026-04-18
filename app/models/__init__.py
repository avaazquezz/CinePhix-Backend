"""SQLAlchemy models for CinePhix."""

from app.models.user import User, UserPreferences, RefreshToken, MagicLink
from app.models.watchlist import WatchlistItem
from app.models.favorite import Favorite
from app.models.review import Review
from app.models.review_vote import ReviewVote, VoteType
from app.models.user_stats import UserStats
from app.models.follow import UserFollow
from app.models.list import List
from app.models.list_item import ListItem
from app.models.activity_feed import ActivityFeed
from app.models.notification import Notification
from app.models.user_pro import UserPro
from app.models.trakt_connection import TraktConnection
from app.models.watched_history import WatchedHistory
from app.models.list_comment import ListComment

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
    "List",
    "ListItem",
    "ActivityFeed",
    "Notification",
    "UserPro",
    "TraktConnection",
]
