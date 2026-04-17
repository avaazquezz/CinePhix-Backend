"""Unit tests for authentication service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.auth_service import AuthService
from app.schemas.auth import UserRegister, UserLogin


class TestAuthService:
    """Tests for AuthService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService with mock db."""
        return AuthService(mock_db)

    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a valid hash."""
        from app.utils.security import hash_password, verify_password

        password = "securepassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_create_access_token(self):
        """Test JWT access token creation."""
        from app.utils.security import create_access_token, decode_token

        token = create_access_token(data={"sub": "test-user-id", "email": "test@example.com"})
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "test-user-id"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test JWT refresh token creation."""
        from app.utils.security import create_refresh_token, decode_token

        token = create_refresh_token(data={"sub": "test-user-id"})
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "test-user-id"
        assert payload["type"] == "refresh"

    def test_generate_magic_link_token(self):
        """Test magic link token generation."""
        from app.utils.security import generate_magic_link_token, verify_magic_link_token

        raw_token, hashed_token = generate_magic_link_token()

        assert len(raw_token) > 20
        assert len(hashed_token) == 64  # SHA256 hex digest
        assert verify_magic_link_token(raw_token, hashed_token) is True
        assert verify_magic_link_token("wrong-token", hashed_token) is False

    def test_hash_token_produces_consistent_output(self):
        """Test that hash_token is deterministic."""
        from app.utils.security import hash_token

        token = "test-token-123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)

        assert hash1 == hash2
        assert len(hash1) == 64

    @pytest.mark.asyncio
    async def test_register_with_password_creates_user(self, auth_service, mock_db):
        """Test user registration creates user with hashed password."""
        # Setup mock to return no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = UserRegister(
            email="test@example.com",
            password="securepassword123",
            username="testuser",
        )

        # Mock flush to set id
        async def mock_flush():
            pass

        mock_db.flush = mock_flush

        user = await auth_service.register_with_password(data)

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password_hash is not None
        assert user.password_hash.startswith("$argon2")

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, auth_service, mock_db):
        """Test registration fails when email already exists."""
        # Mock existing user
        mock_result = MagicMock()
        existing_user = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        data = UserRegister(
            email="existing@example.com",
            password="securepassword123",
            username="newuser",
        )

        with pytest.raises(ValueError, match="already registered"):
            await auth_service.register_with_password(data)

    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials(self, auth_service, mock_db):
        """Test authentication with valid credentials."""
        from app.utils.security import hash_password

        # Create mock user with hashed password
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = hash_password("correctpassword")
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        data = UserLogin(email="test@example.com", password="correctpassword")
        user = await auth_service.authenticate(data)

        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_service, mock_db):
        """Test authentication fails with wrong password."""
        mock_user = MagicMock()
        mock_user.password_hash = hash_password("correctpassword")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        data = UserLogin(email="test@example.com", password="wrongpassword")

        with pytest.raises(ValueError, match="Invalid credentials"):
            await auth_service.authenticate(data)


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_argon2_hash_verification(self):
        """Test argon2 hash and verify cycle."""
        from app.utils.security import hash_password, verify_password

        password = "TestPassword123!@#"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        from app.utils.security import hash_password

        password = "SamePassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True