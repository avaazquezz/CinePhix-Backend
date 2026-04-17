"""Authentication service with user management and JWT tokens."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserPreferences, RefreshToken, MagicLink
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, MagicLinkRequest, GoogleOAuthRequest
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    generate_magic_link_token,
    generate_refresh_token,
    verify_magic_link_token,
)
from app.config import settings


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_with_password(self, data: UserRegister) -> User:
        """Register a new user with email and password."""
        # Check if email or username already exists
        existing = await self.db.execute(
            select(User).where((User.email == data.email) | (User.username == data.username))
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email or username already registered")

        # Create user
        user = User(
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.flush()

        # Create default preferences
        preferences = UserPreferences(user_id=user.id)
        self.db.add(preferences)
        await self.db.flush()

        return user

    async def authenticate(self, data: UserLogin) -> User:
        """Authenticate user with email and password."""
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise ValueError("Invalid credentials")

        if not verify_password(data.password, user.password_hash):
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("Account is disabled")

        return user

    async def create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

        # Create refresh token
        refresh_token = generate_refresh_token()
        token_hash = hash_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        # Store refresh token hash
        stored_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(stored_token)
        await self.db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        stored_token = result.scalar_one_or_none()

        if not stored_token:
            raise ValueError("Invalid or expired refresh token")

        # Get user
        user_result = await self.db.execute(select(User).where(User.id == stored_token.user_id))
        user = user_result.scalar_one_or_none()

        if not user or not user.is_active:
            raise ValueError("User not found or disabled")

        # Revoke old refresh token
        stored_token.revoked_at = datetime.now(timezone.utc)

        # Create new tokens
        return await self.create_tokens(user)

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a refresh token (logout)."""
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one_or_none()

        if stored_token:
            stored_token.revoked_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def create_magic_link(self, data: MagicLinkRequest) -> str | None:
        """Create and return magic link token for email."""
        # Check if user exists
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        raw_token, hashed_token = generate_magic_link_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        magic_link = MagicLink(
            email=data.email,
            token_hash=hashed_token,
            expires_at=expires_at,
        )
        self.db.add(magic_link)
        await self.db.flush()

        # Return the raw token (will be encoded in URL)
        return raw_token

    async def verify_magic_link(self, raw_token: str) -> User | None:
        """Verify magic link token and return user."""
        # Find all non-used magic links and check hash
        result = await self.db.execute(
            select(MagicLink).where(
                MagicLink.used_at.is_(None),
                MagicLink.expires_at > datetime.now(timezone.utc),
            )
        )
        magic_links = result.scalars().all()

        for magic_link in magic_links:
            if verify_magic_link_token(raw_token, magic_link.token_hash):
                # Find user
                user_result = await self.db.execute(select(User).where(User.email == magic_link.email))
                user = user_result.scalar_one_or_none()

                if user:
                    # Mark as used
                    magic_link.used_at = datetime.now(timezone.utc)
                    await self.db.flush()
                    return user

        return None

    async def authenticate_with_google(self, code: str, redirect_uri: str) -> tuple[User, TokenResponse]:
        """Authenticate or register user via Google OAuth."""
        import httpx

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_response.json()
            access_token = token_data.get("access_token")

        # Get user info from Google
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            google_user = user_response.json()

        email = google_user.get("email")
        google_id = google_user.get("id")
        name = google_user.get("name")
        picture = google_user.get("picture")

        if not email:
            raise ValueError("Could not get email from Google")

        # Find or create user
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            # Create new user with Google OAuth
            username = email.split("@")[0].replace(".", "_")
            # Ensure unique username
            existing_username = await self.db.execute(select(User).where(User.username == username))
            counter = 1
            while existing_username.scalar_one_or_none():
                username = f"{email.split('@')[0].replace('.', '_')}_{counter}"
                counter += 1

            user = User(
                email=email,
                username=username,
                display_name=name,
                avatar_url=picture,
                oauth_provider="google",
                oauth_subject=google_id,
            )
            self.db.add(user)
            await self.db.flush()

            # Create default preferences
            preferences = UserPreferences(user_id=user.id)
            self.db.add(preferences)
            await self.db.flush()

        return user, await self.create_tokens(user)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()