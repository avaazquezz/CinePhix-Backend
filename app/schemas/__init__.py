"""Pydantic schemas for request/response validation."""

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    MagicLinkRequest,
    MagicLinkVerify,
    RefreshRequest,
    GoogleOAuthRequest,
)
from app.schemas.user import UserResponse, UserUpdate, UserPreferencesResponse, UserPreferencesUpdate
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistReorder
from app.schemas.favorite import FavoriteCreate, FavoriteResponse, FavoriteCheck
from app.schemas.media import TMDBMovieDetail, TMDBSearchResponse

__all__ = [
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "MagicLinkRequest",
    "MagicLinkVerify",
    "RefreshRequest",
    "GoogleOAuthRequest",
    "UserResponse",
    "UserUpdate",
    "UserPreferencesResponse",
    "UserPreferencesUpdate",
    "WatchlistItemCreate",
    "WatchlistItemResponse",
    "WatchlistReorder",
    "FavoriteCreate",
    "FavoriteResponse",
    "FavoriteCheck",
    "TMDBMovieDetail",
    "TMDBSearchResponse",
]