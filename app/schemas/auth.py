"""Pydantic schemas for authentication."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration with email and password."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class MagicLinkRequest(BaseModel):
    """Schema for requesting a magic link."""

    email: EmailStr


class MagicLinkVerify(BaseModel):
    """Schema for verifying a magic link token (used in URL query)."""

    token: str


class RefreshRequest(BaseModel):
    """Schema for refreshing access token."""

    refresh_token: str


class GoogleOAuthRequest(BaseModel):
    """Schema for handling Google OAuth callback."""

    code: str  # Authorization code from Google
    redirect_uri: str