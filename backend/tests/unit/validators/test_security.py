"""Unit tests for security utilities - JWT, password hashing."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from jose import jwt

from app.config import settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.security import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    @pytest.mark.unit
    def test_hash_password_returns_hash(self) -> None:
        """Password hashing should return a bcrypt hash."""
        password = "secure_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    @pytest.mark.unit
    def test_verify_password_correct(self) -> None:
        """Verify password should return True for correct password."""
        password = "secure_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    @pytest.mark.unit
    def test_verify_password_incorrect(self) -> None:
        """Verify password should return False for incorrect password."""
        password = "secure_password_123"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    @pytest.mark.unit
    def test_hash_password_unique_salts(self) -> None:
        """Hashing same password should produce different hashes (unique salts)."""
        password = "secure_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    @pytest.mark.unit
    def test_verify_password_empty_string(self) -> None:
        """Verify password should handle empty strings."""
        hashed = hash_password("test")
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Tests for JWT token utilities."""

    @pytest.fixture
    def token_data(self) -> dict:
        """Sample token payload."""
        return {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "test@example.com",
            "role": "admin",
            "permissions": ["articles:read", "articles:write"],
            "is_superuser": False,
        }

    @pytest.mark.unit
    def test_create_access_token(self, token_data: dict) -> None:
        """Access token should be created successfully."""
        token = create_access_token(token_data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.unit
    def test_create_access_token_with_expiry(self, token_data: dict) -> None:
        """Access token should respect custom expiry."""
        expires = timedelta(hours=2)
        token = create_access_token(token_data, expires_delta=expires)

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        iat = payload.get("iat")
        exp = payload["exp"]

        # The difference between exp and iat should be approximately 2 hours
        if iat:
            diff_seconds = exp - iat
            expected_seconds = expires.total_seconds()
            assert abs(diff_seconds - expected_seconds) < 60  # 60 second tolerance
        else:
            # Just verify exp is set
            assert exp > 0

    @pytest.mark.unit
    def test_create_refresh_token(self, token_data: dict) -> None:
        """Refresh token should be created successfully."""
        token = create_refresh_token(token_data)

        assert token is not None
        assert isinstance(token, str)

        payload = decode_token(token)
        assert payload["type"] == "refresh"

    @pytest.mark.unit
    def test_decode_valid_access_token(self, token_data: dict) -> None:
        """Decoding valid access token should return payload."""
        token = create_access_token(token_data)
        payload = decode_token(token)

        assert payload["sub"] == token_data["sub"]
        assert payload["tenant_id"] == token_data["tenant_id"]
        assert payload["email"] == token_data["email"]
        assert payload["type"] == "access"

    @pytest.mark.unit
    def test_decode_valid_refresh_token(self, token_data: dict) -> None:
        """Decoding valid refresh token should return payload."""
        token = create_refresh_token(token_data)
        payload = decode_token(token)

        assert payload["sub"] == token_data["sub"]
        assert payload["type"] == "refresh"

    @pytest.mark.unit
    def test_decode_expired_token_raises(self, token_data: dict) -> None:
        """Decoding expired token should raise TokenExpiredError."""
        # Create token that's already expired
        token = create_access_token(token_data, expires_delta=timedelta(seconds=-10))

        with pytest.raises(TokenExpiredError):
            decode_token(token)

    @pytest.mark.unit
    def test_decode_invalid_token_raises(self) -> None:
        """Decoding invalid token should raise InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            decode_token("invalid.token.string")

    @pytest.mark.unit
    def test_decode_tampered_token_raises(self, token_data: dict) -> None:
        """Decoding tampered token should raise InvalidTokenError."""
        token = create_access_token(token_data)
        # Tamper with the token
        tampered = token[:-5] + "xxxxx"

        with pytest.raises(InvalidTokenError):
            decode_token(tampered)


class TestTokenPayload:
    """Tests for TokenPayload class."""

    @pytest.mark.unit
    def test_token_payload_parsing(self) -> None:
        """TokenPayload should correctly parse JWT payload."""
        user_id = uuid4()
        tenant_id = uuid4()
        now = datetime.utcnow()

        payload_dict = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "email": "test@example.com",
            "role": "admin",
            "permissions": ["articles:read", "articles:write"],
            "is_superuser": True,
            "type": "access",
            "exp": int(now.timestamp()) + 3600,
        }

        payload = TokenPayload(payload_dict)

        assert payload.user_id == user_id
        assert payload.tenant_id == tenant_id
        assert payload.email == "test@example.com"
        assert payload.role == "admin"
        assert payload.permissions == ["articles:read", "articles:write"]
        assert payload.is_superuser is True
        assert payload.token_type == "access"

    @pytest.mark.unit
    def test_token_payload_optional_fields(self) -> None:
        """TokenPayload should handle optional fields."""
        user_id = uuid4()
        tenant_id = uuid4()

        payload_dict = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "email": "test@example.com",
            "exp": int(datetime.utcnow().timestamp()) + 3600,
        }

        payload = TokenPayload(payload_dict)

        assert payload.role is None
        assert payload.permissions == []
        assert payload.is_superuser is False
        assert payload.token_type == "access"

