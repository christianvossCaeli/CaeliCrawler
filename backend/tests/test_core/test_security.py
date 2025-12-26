"""Unit tests for security utilities."""

import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.core.security import (
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SSE_TICKET_EXPIRE_SECONDS,
    MAX_SESSIONS_PER_USER,
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
    create_refresh_token_response,
    create_tokens_for_session,
    create_sse_ticket,
    decode_sse_ticket,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test that password hashing creates a hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        # bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")

    def test_hash_password_different_each_time(self):
        """Test that the same password produces different hashes (due to salt)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that correct password is verified."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password is rejected."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_with_special_characters(self):
        """Test password verification with special characters."""
        password = "p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_with_unicode(self):
        """Test password verification with unicode characters."""
        password = "пароль密码كلمة"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


class TestAccessToken:
    """Tests for JWT access token functions."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = uuid4()
        role = "EDITOR"

        token = create_access_token(user_id, role)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_session_id(self):
        """Test access token creation with session ID."""
        user_id = uuid4()
        role = "EDITOR"
        session_id = uuid4()

        token = create_access_token(user_id, role, session_id)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sid"] == str(session_id)

    def test_decode_access_token(self):
        """Test access token decoding."""
        user_id = uuid4()
        role = "ADMIN"

        token = create_access_token(user_id, role)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["role"] == role
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        invalid_token = "invalid.token.here"

        payload = decode_access_token(invalid_token)

        assert payload is None

    def test_decode_expired_token(self):
        """Test decoding an expired token returns None."""
        user_id = uuid4()
        role = "VIEWER"

        # Create token that expires immediately
        token = create_access_token(
            user_id, role,
            expires_delta=timedelta(seconds=-1)
        )

        payload = decode_access_token(token)

        assert payload is None

    def test_access_token_expiry_is_set(self):
        """Test that access token has correct expiry."""
        user_id = uuid4()
        role = "EDITOR"

        token = create_access_token(user_id, role)
        payload = decode_access_token(token)

        assert payload is not None
        assert "exp" in payload

        # Token should expire within expected time frame (with some margin)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Allow 5 second margin for test execution time
        assert abs((exp_time - expected_exp).total_seconds()) < 5


class TestRefreshToken:
    """Tests for refresh token functions."""

    def test_generate_refresh_token(self):
        """Test refresh token generation."""
        token = generate_refresh_token()

        assert isinstance(token, str)
        assert len(token) > 0
        # URL-safe base64 characters only
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_generate_refresh_token_unique(self):
        """Test that refresh tokens are unique."""
        tokens = [generate_refresh_token() for _ in range(100)]

        assert len(set(tokens)) == 100

    def test_hash_refresh_token(self):
        """Test refresh token hashing."""
        token = generate_refresh_token()
        hashed = hash_refresh_token(token)

        assert isinstance(hashed, str)
        # SHA-256 produces 64 hex characters
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_refresh_token_deterministic(self):
        """Test that same token produces same hash."""
        token = generate_refresh_token()
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)

        assert hash1 == hash2

    def test_verify_refresh_token_valid(self):
        """Test verifying a valid refresh token."""
        token = generate_refresh_token()
        token_hash = hash_refresh_token(token)

        assert verify_refresh_token(token, token_hash) is True

    def test_verify_refresh_token_invalid(self):
        """Test verifying an invalid refresh token."""
        token = generate_refresh_token()
        wrong_token = generate_refresh_token()
        token_hash = hash_refresh_token(token)

        assert verify_refresh_token(wrong_token, token_hash) is False

    def test_create_refresh_token_response(self):
        """Test creating refresh token response."""
        user_id = uuid4()
        role = "EDITOR"
        session_id = uuid4()

        raw_token, token_hash, expires_at = create_refresh_token_response(
            user_id, role, session_id
        )

        assert isinstance(raw_token, str)
        assert isinstance(token_hash, str)
        assert isinstance(expires_at, datetime)

        # Verify the hash matches the token
        assert verify_refresh_token(raw_token, token_hash)

        # Check expiry is in the future
        expected_exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        assert abs((expires_at - expected_exp).total_seconds()) < 5


class TestTokensForSession:
    """Tests for combined session token creation."""

    def test_create_tokens_for_session(self):
        """Test creating both tokens for a session."""
        user_id = uuid4()
        role = "ADMIN"
        session_id = uuid4()

        tokens = create_tokens_for_session(user_id, role, session_id)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "refresh_token_hash" in tokens
        assert "refresh_expires_at" in tokens
        assert "access_token_expires_in" in tokens
        assert "refresh_token_expires_in" in tokens

    def test_tokens_for_session_are_valid(self):
        """Test that created tokens are valid."""
        user_id = uuid4()
        role = "EDITOR"
        session_id = uuid4()

        tokens = create_tokens_for_session(user_id, role, session_id)

        # Access token can be decoded
        payload = decode_access_token(tokens["access_token"])
        assert payload is not None
        assert payload["sub"] == str(user_id)

        # Refresh token hash matches
        assert verify_refresh_token(
            tokens["refresh_token"],
            tokens["refresh_token_hash"]
        )

    def test_tokens_for_session_expiry_values(self):
        """Test that expiry values are correct."""
        user_id = uuid4()
        role = "VIEWER"
        session_id = uuid4()

        tokens = create_tokens_for_session(user_id, role, session_id)

        assert tokens["access_token_expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60
        assert tokens["refresh_token_expires_in"] == REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


class TestSSETicket:
    """Tests for SSE ticket functions."""

    def test_create_sse_ticket(self):
        """Test SSE ticket creation."""
        user_id = uuid4()
        role = "VIEWER"

        ticket = create_sse_ticket(user_id, role)

        assert isinstance(ticket, str)
        assert len(ticket) > 0

    def test_decode_sse_ticket(self):
        """Test SSE ticket decoding."""
        user_id = uuid4()
        role = "EDITOR"

        ticket = create_sse_ticket(user_id, role)
        payload = decode_sse_ticket(ticket)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["role"] == role
        assert payload["type"] == "sse_ticket"

    def test_decode_sse_ticket_rejects_access_token(self):
        """Test that regular access token is rejected as SSE ticket."""
        user_id = uuid4()
        role = "VIEWER"

        access_token = create_access_token(user_id, role)
        payload = decode_sse_ticket(access_token)

        # Should be rejected because type is "access" not "sse_ticket"
        assert payload is None

    def test_decode_invalid_sse_ticket(self):
        """Test decoding invalid SSE ticket returns None."""
        invalid_ticket = "invalid.ticket.here"

        payload = decode_sse_ticket(invalid_ticket)

        assert payload is None

    def test_sse_ticket_short_expiry(self):
        """Test that SSE ticket expires quickly."""
        user_id = uuid4()
        role = "VIEWER"

        ticket = create_sse_ticket(user_id, role)
        payload = decode_sse_ticket(ticket)

        assert payload is not None
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(seconds=SSE_TICKET_EXPIRE_SECONDS)

        # Allow 5 second margin
        assert abs((exp_time - expected_exp).total_seconds()) < 5


class TestConstants:
    """Tests for security constants."""

    def test_algorithm_is_hs256(self):
        """Test that algorithm is HS256."""
        assert ALGORITHM == "HS256"

    def test_access_token_expire_reasonable(self):
        """Test that access token expiry is reasonable."""
        # Should be short for security (15-60 minutes)
        assert 15 <= ACCESS_TOKEN_EXPIRE_MINUTES <= 60

    def test_refresh_token_expire_reasonable(self):
        """Test that refresh token expiry is reasonable."""
        # Should be days to weeks (7-30 days)
        assert 7 <= REFRESH_TOKEN_EXPIRE_DAYS <= 30

    def test_sse_ticket_expire_short(self):
        """Test that SSE ticket expiry is very short."""
        # Should be seconds (10-60 seconds)
        assert 10 <= SSE_TICKET_EXPIRE_SECONDS <= 60

    def test_max_sessions_per_user_reasonable(self):
        """Test that max sessions limit is reasonable."""
        # Should be 3-10 sessions
        assert 3 <= MAX_SESSIONS_PER_USER <= 10
