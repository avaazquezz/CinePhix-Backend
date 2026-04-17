"""Authentication routes: register, login, magic links, OAuth, refresh."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    MagicLinkRequest,
    MagicLinkVerify,
    RefreshRequest,
    GoogleOAuthRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.dependencies import CurrentUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    service = AuthService(db)
    email_service = EmailService()

    try:
        user = await service.register_with_password(data)
        tokens = await service.create_tokens(user)
        # Send welcome email (non-blocking, won't fail registration)
        await email_service.send_welcome_email(user.email, user.username)
        return tokens
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    service = AuthService(db)

    try:
        user = await service.authenticate(data)
        return await service.create_tokens(user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(data: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    """Request a magic link to be sent to email (for login without password)."""
    service = AuthService(db)
    email_service = EmailService()

    # Always return 202 to prevent email enumeration
    raw_token = await service.create_magic_link(data)

    if raw_token and settings.resend_api_key:
        await email_service.send_magic_link(data.email, raw_token)

    return {"message": "If the email exists, a magic link has been sent"}


@router.get("/magic-link/verify", response_model=TokenResponse)
async def verify_magic_link(
    token: str = Query(..., description="Magic link token from email"),
    db: AsyncSession = Depends(get_db),
):
    """Verify magic link token and return JWT tokens."""
    service = AuthService(db)

    user = await service.verify_magic_link(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link",
        )

    return await service.create_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    service = AuthService(db)

    try:
        return await service.refresh_access_token(data.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Logout by revoking refresh token."""
    service = AuthService(db)
    await service.revoke_refresh_token(data.refresh_token)


@router.post("/google", response_model=TokenResponse)
async def google_oauth(data: GoogleOAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with Google OAuth."""
    service = AuthService(db)

    try:
        user, tokens = await service.authenticate_with_google(data.code, data.redirect_uri)
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get current authenticated user."""
    return current_user


# Import settings for email check
from app.config import settings