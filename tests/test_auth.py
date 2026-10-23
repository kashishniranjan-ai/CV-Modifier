"""
Tests for local offline user authentication, PBKDF2 hashing, lockout, and admin reset.
"""

import time
import pytest
from app.database import (
    init_db,
    create_user,
    authenticate_user,
    get_user_by_username,
    admin_reset_password,
    delete_user,
    get_user_count,
)
from app.security import hash_password, verify_password


@pytest.fixture(autouse=True)
def setup_auth_db():
    init_db()


def test_pbkdf2_hashing():
    pwd = "SecretPassword123"
    h1, s1 = hash_password(pwd)
    assert len(h1) == 64  # SHA-256 hex length
    assert len(s1) == 32  # 16 bytes hex

    assert verify_password(pwd, h1, s1) is True
    assert verify_password("WrongPassword", h1, s1) is False


def test_user_creation_and_authentication():
    username = f"test_recruiter_{int(time.time() * 1000)}"
    success, msg = create_user(
        username=username,
        password="MySecurePassword",
        full_name="Test Recruiter",
        email="test@scalexpro.com",
        role="Recruiter",
    )
    assert success is True

    # Duplicate username fails
    dup_success, _ = create_user(
        username=username,
        password="OtherPassword",
        full_name="Duplicate",
    )
    assert dup_success is False

    # Authenticate with correct credentials
    auth_ok, user_data, auth_msg = authenticate_user(username, "MySecurePassword")
    assert auth_ok is True
    assert user_data is not None
    assert user_data["username"] == username
    assert user_data["role"] == "Recruiter"
    assert "password_hash" not in user_data  # sensitive data stripped

    # Authenticate with incorrect password
    bad_ok, bad_data, bad_msg = authenticate_user(username, "WrongPassword")
    assert bad_ok is False
    assert bad_data is None
    assert "remaining" in bad_msg.lower()


def test_lockout_after_5_failed_attempts():
    username = f"locked_user_{int(time.time() * 1000)}"
    create_user(username, "CorrectPassword", "Locked User")

    # 4 failed attempts
    for _ in range(4):
        ok, _, _ = authenticate_user(username, "BadPassword")
        assert ok is False

    # 5th failed attempt triggers lockout
    ok5, _, msg5 = authenticate_user(username, "BadPassword")
    assert ok5 is False
    assert "locked for 60 seconds" in msg5.lower()

    # Immediate attempt with even the CORRECT password is blocked by lockout
    blocked_ok, _, blocked_msg = authenticate_user(username, "CorrectPassword")
    assert blocked_ok is False
    assert "locked" in blocked_msg.lower()


def test_admin_reset_password():
    username = f"reset_user_{int(time.time() * 1000)}"
    create_user(username, "InitialPassword", "Reset User")

    user = get_user_by_username(username)
    assert user is not None

    # Admin resets password
    reset_ok, _ = admin_reset_password(user["id"], "BrandNewPassword456")
    assert reset_ok is True

    # Old password no longer works
    old_ok, _, _ = authenticate_user(username, "InitialPassword")
    assert old_ok is False

    # New password works
    new_ok, udata, _ = authenticate_user(username, "BrandNewPassword456")
    assert new_ok is True
    assert udata["username"] == username
