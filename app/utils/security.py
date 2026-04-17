"""Security utilities for authentication (JWT, password hashing)."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context (Argon2id - recommended for password hashing)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "jti": str(uuid4()), "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.refresh_token_expire_days))
    to_encode.update({"exp": expire, "jti": str(uuid4()), "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a token for storage (avoids storing raw tokens)."""
    return sha256(token.encode()).hexdigest()


def generate_magic_link_token() -> tuple[str, str]:
    """Generate a magic link token and its hash.

    Returns:
        tuple: (raw_token, hashed_token)
    """
    raw_token = token_urlsafe(32)
    hashed_token = hash_token(raw_token)
    return raw_token, hashed_token


def generate_refresh_token() -> str:
    """Generate a secure random refresh token."""
    return token_urlsafe(32)


def verify_magic_link_token(raw_token: str, hashed_token: str) -> bool:
    """Verify a magic link token against its hash."""
    return hash_token(raw_token) == hashed_token