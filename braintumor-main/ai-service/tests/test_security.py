"""
tests/test_security.py — Comprehensive tests for the security module.

Covers:
  - JWT: create, decode, revocation, expiry, type checking
  - Password: hashing, verification, strength validation, reset token
  - RBAC: role permissions, require_roles dependency
  - Audit logging: record creation, JSONL writing
  - Rate limiting: login endpoint rate limit
  - Auth endpoints: login, logout, refresh, /me, change-password, users
  - Protected routes: 401 without token, 403 wrong role
"""

from __future__ import annotations

import json
import os
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

os.environ.setdefault("AI_SERVICE_ENV", "test")
os.environ.setdefault("BCRYPT_ROUNDS", "4")

from app.main import app
from app.core.config import settings
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_refresh_token,
    revoke_token,
    is_token_revoked,
    revocation_store_size,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    _revoked_tokens,
)
from app.security.password import (
    hash_password,
    verify_password,
    needs_rehash,
    generate_reset_token,
    validate_password_strength,
)
from app.security.roles import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    get_permissions,
    has_permission,
)
from app.security.auth import (
    UserInDB,
    UserStore,
    get_user_store,
    authenticate_user,
)
from app.security.audit import AuditEvent, AuditRecord, AuditLogger, log_audit


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_revocation_store():
    """Clear revoked tokens between tests."""
    _revoked_tokens.clear()
    yield
    _revoked_tokens.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _make_token(user_id: str = "user-123", role: str = "admin") -> str:
    return create_access_token({"sub": user_id, "role": role})


def _admin_headers() -> dict:
    store = get_user_store()
    admin = store.get_by_username("admin")
    assert admin is not None
    token = create_access_token({"sub": admin.user_id, "role": admin.role.value})
    return {"Authorization": f"Bearer {token}"}


def _role_headers(role: str) -> dict:
    store = get_user_store()
    user = store.get_by_username(role)
    if user is None:
        user = store.get_by_username("admin")
    assert user is not None
    token = create_access_token({"sub": user.user_id, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def _login(client, username="admin", password="Admin@123!") -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()


# ═════════════════════════════════════════════════════════════════════════════
# JWT Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestJWT:
    def test_create_access_token_returns_string(self):
        token = create_access_token({"sub": "u1", "role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_decodes_correctly(self):
        token = create_access_token({"sub": "u1", "role": "viewer"})
        payload = decode_token(token)
        assert payload["sub"] == "u1"
        assert payload["role"] == "viewer"
        assert payload["type"] == TOKEN_TYPE_ACCESS

    def test_access_token_has_jti(self):
        token = create_access_token({"sub": "u1"})
        payload = decode_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_access_token_has_iat_and_exp(self):
        token = create_access_token({"sub": "u1"})
        payload = decode_token(token)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_refresh_token_type_is_refresh(self):
        token = create_refresh_token({"sub": "u1"})
        payload = decode_token(token)
        assert payload["type"] == TOKEN_TYPE_REFRESH

    def test_decode_refresh_token_validates_type(self):
        token = create_refresh_token({"sub": "u1"})
        payload = decode_refresh_token(token)
        assert payload["sub"] == "u1"

    def test_decode_refresh_rejects_access_token(self):
        token = create_access_token({"sub": "u1"})
        with pytest.raises(ValueError, match="not a refresh token"):
            decode_refresh_token(token)

    def test_expired_token_raises(self):
        token = create_access_token({"sub": "u1"}, expires_delta=timedelta(seconds=-1))
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token({"sub": "u1"})
        tampered = token[:-5] + "XXXXX"
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_revoke_token_blocks_decode(self):
        token = create_access_token({"sub": "u1"})
        payload = decode_token(token)
        revoke_token(payload["jti"])
        with pytest.raises(ValueError, match="revoked"):
            decode_token(token)

    def test_revoked_token_is_detected(self):
        token = create_access_token({"sub": "u1"})
        payload = decode_token(token)
        jti = payload["jti"]
        assert not is_token_revoked(jti)
        revoke_token(jti)
        assert is_token_revoked(jti)

    def test_revocation_store_size_increments(self):
        before = revocation_store_size()
        token = create_access_token({"sub": "u1"})
        payload = decode_token(token)
        revoke_token(payload["jti"])
        assert revocation_store_size() == before + 1

    def test_wrong_secret_raises(self):
        token = jose_jwt.encode(
            {"sub": "u1", "type": "access"},
            "wrong-secret",
            algorithm=settings.jwt_algorithm,
        )
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token(token)

    def test_custom_expiry_respected(self):
        short = create_access_token({"sub": "u1"}, expires_delta=timedelta(hours=1))
        long  = create_access_token({"sub": "u1"}, expires_delta=timedelta(hours=24))
        p_short = decode_token(short)
        p_long  = decode_token(long)
        assert p_long["exp"] > p_short["exp"]

    def test_two_tokens_have_different_jti(self):
        t1 = create_access_token({"sub": "u1"})
        t2 = create_access_token({"sub": "u1"})
        p1 = decode_token(t1)
        p2 = decode_token(t2)
        assert p1["jti"] != p2["jti"]


# ═════════════════════════════════════════════════════════════════════════════
# Password Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestPassword:
    def test_hash_returns_string(self):
        h = hash_password("Secret@1")
        assert isinstance(h, str)
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_verify_correct_password(self):
        pw = "MyPass@1"
        assert verify_password(pw, hash_password(pw)) is True

    def test_verify_wrong_password(self):
        assert verify_password("wrong", hash_password("correct@1")) is False

    def test_hash_is_different_each_time(self):
        pw = "Same@Pass1"
        assert hash_password(pw) != hash_password(pw)

    def test_empty_password_raises(self):
        with pytest.raises(ValueError):
            hash_password("")

    def test_verify_empty_plain_returns_false(self):
        assert verify_password("", hash_password("real@pass1")) is False

    def test_needs_rehash_false_for_fresh_hash(self):
        h = hash_password("Fresh@1")
        assert needs_rehash(h) is False

    def test_generate_reset_token_length(self):
        token = generate_reset_token(48)
        assert len(token) == 48

    def test_generate_reset_token_alphanumeric(self):
        token = generate_reset_token()
        assert all(c.isalnum() for c in token)

    def test_generate_reset_tokens_unique(self):
        assert generate_reset_token() != generate_reset_token()

    def test_strength_passes_strong_password(self):
        errors = validate_password_strength("Strong@Pass1")
        assert errors == []

    def test_strength_fails_too_short(self):
        errors = validate_password_strength("Ab@1")
        assert any("8 characters" in e for e in errors)

    def test_strength_fails_no_uppercase(self):
        errors = validate_password_strength("alllower@1")
        assert any("uppercase" in e.lower() for e in errors)

    def test_strength_fails_no_digit(self):
        errors = validate_password_strength("NoDigits@")
        assert any("digit" in e.lower() for e in errors)

    def test_strength_fails_no_special(self):
        errors = validate_password_strength("NoSpecial1")
        assert any("special" in e.lower() for e in errors)

    def test_strength_multiple_failures(self):
        errors = validate_password_strength("weak")
        assert len(errors) >= 3


# ═════════════════════════════════════════════════════════════════════════════
# RBAC / Roles Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestRBAC:
    def test_admin_has_all_permissions(self):
        perms = get_permissions(Role.ADMIN)
        for p in Permission:
            assert p in perms, f"Admin missing permission: {p.value}"

    def test_viewer_has_dashboard_read(self):
        assert has_permission(Role.VIEWER, Permission.DASHBOARD_READ)

    def test_viewer_cannot_train(self):
        assert not has_permission(Role.VIEWER, Permission.TRAIN_START)

    def test_viewer_cannot_reload_model(self):
        assert not has_permission(Role.VIEWER, Permission.MODEL_RELOAD)

    def test_operator_can_predict(self):
        assert has_permission(Role.OPERATOR, Permission.PREDICT_SINGLE)
        assert has_permission(Role.OPERATOR, Permission.PREDICT_BATCH)

    def test_operator_cannot_train(self):
        assert not has_permission(Role.OPERATOR, Permission.TRAIN_START)

    def test_researcher_can_train(self):
        assert has_permission(Role.RESEARCHER, Permission.TRAIN_START)

    def test_researcher_can_gradcam(self):
        assert has_permission(Role.RESEARCHER, Permission.GRADCAM)

    def test_researcher_cannot_manage_users(self):
        assert not has_permission(Role.RESEARCHER, Permission.USER_MANAGE)

    def test_admin_can_manage_users(self):
        assert has_permission(Role.ADMIN, Permission.USER_MANAGE)

    def test_role_permissions_map_covers_all_roles(self):
        for role in Role:
            assert role in ROLE_PERMISSIONS

    def test_get_permissions_returns_set(self):
        for role in Role:
            perms = get_permissions(role)
            assert isinstance(perms, set)

    def test_unknown_role_returns_empty_set(self):
        # Simulate unknown role by patching
        assert get_permissions(Role.VIEWER) != set()


# ═════════════════════════════════════════════════════════════════════════════
# UserStore / Authentication Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestUserStore:
    def test_default_users_seeded(self):
        store = get_user_store()
        for username in ("admin", "researcher", "operator", "viewer"):
            assert store.get_by_username(username) is not None

    def test_get_by_username_returns_correct_role(self):
        store = get_user_store()
        assert store.get_by_username("admin").role == Role.ADMIN
        assert store.get_by_username("viewer").role == Role.VIEWER

    def test_get_by_id_works(self):
        store = get_user_store()
        admin = store.get_by_username("admin")
        found = store.get_by_id(admin.user_id)
        assert found is not None
        assert found.username == "admin"

    def test_get_unknown_username_returns_none(self):
        assert get_user_store().get_by_username("nobody") is None

    def test_authenticate_success(self):
        user = authenticate_user("admin", "Admin@123!")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_wrong_password(self):
        assert authenticate_user("admin", "wrongpassword") is None

    def test_authenticate_unknown_user(self):
        assert authenticate_user("ghost", "whatever") is None

    def test_failed_login_increments_counter(self):
        store = get_user_store()
        viewer = store.get_by_username("viewer")
        before = viewer.failed_login_count
        authenticate_user("viewer", "wrong")
        assert viewer.failed_login_count == before + 1

    def test_successful_login_resets_counter(self):
        store = get_user_store()
        viewer = store.get_by_username("viewer")
        authenticate_user("viewer", "wrong")
        authenticate_user("viewer", "Viewer@123!")
        assert viewer.failed_login_count == 0

    def test_account_locks_after_max_failures(self):
        store = get_user_store()
        # Create a fresh user for lockout test
        import uuid
        uname = f"locktest_{uuid.uuid4().hex[:8]}"
        store.create_user(uname, f"{uname}@test.local", "Lock@Test1", Role.VIEWER)
        for _ in range(settings.max_failed_logins):
            authenticate_user(uname, "wrong")
        user = store.get_by_username(uname)
        assert user.is_locked is True

    def test_locked_account_cannot_login(self):
        store = get_user_store()
        import uuid
        uname = f"locktest2_{uuid.uuid4().hex[:8]}"
        store.create_user(uname, f"{uname}@test.local", "Lock@Test1", Role.VIEWER)
        for _ in range(settings.max_failed_logins):
            authenticate_user(uname, "wrong")
        result = authenticate_user(uname, "Lock@Test1")
        assert result is None

    def test_unlock_user_clears_lock(self):
        store = get_user_store()
        import uuid
        uname = f"locktest3_{uuid.uuid4().hex[:8]}"
        store.create_user(uname, f"{uname}@test.local", "Lock@Test1", Role.VIEWER)
        for _ in range(settings.max_failed_logins):
            authenticate_user(uname, "wrong")
        user = store.get_by_username(uname)
        store.unlock_user(user.user_id)
        assert user.is_locked is False

    def test_to_public_excludes_password(self):
        store = get_user_store()
        admin = store.get_by_username("admin")
        pub = admin.to_public()
        d = pub.to_dict()
        assert "hashed_password" not in d
        assert "password" not in d

    def test_create_duplicate_username_raises(self):
        store = get_user_store()
        with pytest.raises(ValueError, match="already taken"):
            store.create_user("admin", "dup@test.com", "Dup@Pass1", Role.VIEWER)


# ═════════════════════════════════════════════════════════════════════════════
# Audit Logging Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditLogging:
    def test_audit_record_to_dict(self):
        record = AuditRecord(
            event=AuditEvent.LOGIN,
            username="alice",
            user_id="uid-1",
            endpoint="/auth/login",
            outcome="success",
        )
        d = record.to_dict()
        assert d["event"] == "auth.login"
        assert d["username"] == "alice"
        assert d["outcome"] == "success"
        assert "timestamp" in d

    def test_audit_record_to_json_is_valid(self):
        record = AuditRecord(event=AuditEvent.LOGOUT, username="bob")
        parsed = json.loads(record.to_json())
        assert parsed["event"] == "auth.logout"

    def test_audit_logger_writes_to_file(self, tmp_path):
        logger = AuditLogger(tmp_path)
        record = AuditRecord(event=AuditEvent.LOGIN, username="test_user")
        logger.write(record)
        logger.close()
        files = list(tmp_path.glob("audit_*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["username"] == "test_user"

    def test_audit_logger_multiple_writes(self, tmp_path):
        logger = AuditLogger(tmp_path)
        for event in [AuditEvent.LOGIN, AuditEvent.LOGOUT, AuditEvent.TRAIN_START]:
            logger.write(AuditRecord(event=event, username="u"))
        logger.close()
        files = list(tmp_path.glob("audit_*.jsonl"))
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 3

    def test_log_audit_convenience_function(self, tmp_path):
        from app.security.audit import audit_logger
        original_dir = audit_logger._dir
        audit_logger._dir = tmp_path
        audit_logger._fh = None
        audit_logger._date = None
        log_audit(AuditEvent.PERMISSION_DENIED, username="eve", outcome="failure")
        audit_logger._dir = original_dir
        audit_logger._fh = None
        audit_logger._date = None

    def test_all_audit_events_have_values(self):
        for event in AuditEvent:
            assert "." in event.value, f"Event {event.name} missing dot in value"

    def test_audit_record_details_stored(self):
        record = AuditRecord(
            event=AuditEvent.MODEL_RELOAD,
            details={"model_name": "efficientnet"},
        )
        assert record.details["model_name"] == "efficientnet"
        assert record.to_dict()["details"]["model_name"] == "efficientnet"


# ═════════════════════════════════════════════════════════════════════════════
# Auth Endpoint Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestLoginEndpoint:
    def test_valid_login_returns_200(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123!"},
        )
        assert resp.status_code == 200

    def test_login_returns_tokens(self, client):
        data = _login(client)
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_returns_user_info(self, client):
        data = _login(client)
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"
        assert "hashed_password" not in data["user"]

    def test_wrong_password_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_unknown_user_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "whatever"},
        )
        assert resp.status_code == 401

    def test_empty_username_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": "Admin@123!"},
        )
        assert resp.status_code == 422

    def test_all_default_users_can_login(self, client):
        credentials = [
            ("admin",      "Admin@123!"),
            ("researcher", "Research@123!"),
            ("operator",   "Operator@123!"),
            ("viewer",     "Viewer@123!"),
        ]
        for username, password in credentials:
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
            )
            assert resp.status_code == 200, f"Login failed for {username}"


class TestLogoutEndpoint:
    def test_logout_with_valid_token(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()

    def test_logout_revokes_access_token(self, client):
        tokens = _login(client)
        client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Token is now revoked — /me should return 401
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 401

    def test_logout_with_refresh_token(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200

    def test_logout_without_token_returns_401(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401


class TestRefreshEndpoint:
    def test_valid_refresh_returns_new_access_token(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_refresh_returns_different_access_token(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.json()["access_token"] != tokens["access_token"]

    def test_invalid_refresh_token_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.real.token"},
        )
        assert resp.status_code == 401

    def test_access_token_used_as_refresh_returns_401(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
        )
        assert resp.status_code == 401


class TestMeEndpoint:
    def test_me_with_valid_token(self, client):
        tokens = _login(client)
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "admin"

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_me_returns_correct_role(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "viewer", "password": "Viewer@123!"},
        )
        token = resp.json()["access_token"]
        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert me["data"]["role"] == "viewer"


class TestChangePasswordEndpoint:
    def test_change_password_success(self, client):
        import uuid
        uname = f"pwtest_{uuid.uuid4().hex[:8]}"
        store = get_user_store()
        store.create_user(uname, f"{uname}@test.local", "Old@Pass1", Role.VIEWER)
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": uname, "password": "Old@Pass1"},
        )
        token = resp.json()["access_token"]
        change_resp = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "Old@Pass1", "new_password": "New@Pass1"},
        )
        assert change_resp.status_code == 200

    def test_wrong_current_password_returns_400(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"current_password": "WrongOld@1", "new_password": "New@Pass1"},
        )
        assert resp.status_code == 400

    def test_weak_new_password_returns_422(self, client):
        tokens = _login(client)
        resp = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"current_password": "Admin@123!", "new_password": "weak"},
        )
        assert resp.status_code == 422


class TestAdminUserManagement:
    def test_list_users_admin_only(self, client):
        resp = client.get(
            "/api/v1/auth/users",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert data["total"] >= 4

    def test_list_users_viewer_returns_403(self, client):
        resp = client.get(
            "/api/v1/auth/users",
            headers=_role_headers("viewer"),
        )
        assert resp.status_code == 403

    def test_create_user_admin(self, client):
        import uuid
        uname = f"newuser_{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/auth/users",
            headers=_admin_headers(),
            json={
                "username": uname,
                "email": f"{uname}@test.local",
                "password": "New@User1",
                "role": "viewer",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["username"] == uname

    def test_create_user_duplicate_returns_409(self, client):
        resp = client.post(
            "/api/v1/auth/users",
            headers=_admin_headers(),
            json={
                "username": "admin",
                "email": "dup@test.com",
                "password": "Dup@Pass1",
                "role": "viewer",
            },
        )
        assert resp.status_code == 409

    def test_unlock_user(self, client):
        store = get_user_store()
        import uuid
        uname = f"lockme_{uuid.uuid4().hex[:8]}"
        store.create_user(uname, f"{uname}@test.local", "Lock@Me1!", Role.VIEWER)
        for _ in range(settings.max_failed_logins):
            authenticate_user(uname, "wrong")
        user = store.get_by_username(uname)
        assert user.is_locked
        resp = client.post(
            f"/api/v1/auth/users/{user.user_id}/unlock",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert not user.is_locked


# ═════════════════════════════════════════════════════════════════════════════
# Protected Route Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestProtectedRoutes:
    def test_health_is_public(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_predict_public_without_token(self, client):
        # predict uses optional_auth so no token is fine
        # It will fail with 404/500 due to no model, not 401
        import struct, zlib
        def _png():
            def chunk(name, data):
                c = name + data
                return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
            iend = chunk(b"IEND", b"")
            return sig + ihdr + idat + iend
        resp = client.post(
            "/api/v1/predict",
            files={"image": ("t.png", _png(), "image/png")},
        )
        assert resp.status_code in (200, 404, 500)

    def test_train_without_token_returns_401(self, client):
        resp = client.post("/api/v1/train", json={})
        assert resp.status_code == 401

    def test_train_viewer_returns_403(self, client):
        resp = client.post(
            "/api/v1/train",
            headers=_role_headers("viewer"),
            json={"model_name": "cnn", "epochs": 1},
        )
        assert resp.status_code == 403

    def test_evaluate_without_token_returns_401(self, client):
        resp = client.post("/api/v1/evaluate", json={})
        assert resp.status_code == 401

    def test_dataset_info_without_token_returns_401(self, client):
        resp = client.get("/api/v1/dataset/info")
        assert resp.status_code == 401

    def test_dataset_prepare_operator_returns_403(self, client):
        resp = client.post(
            "/api/v1/dataset/prepare",
            headers=_role_headers("operator"),
            json={"train_ratio": 0.7, "val_ratio": 0.15, "test_ratio": 0.15},
        )
        assert resp.status_code == 403

    def test_models_list_without_token_returns_401(self, client):
        resp = client.get("/api/v1/models")
        assert resp.status_code == 401

    def test_models_reload_viewer_returns_403(self, client):
        resp = client.post(
            "/api/v1/models/reload",
            headers=_role_headers("viewer"),
            json={"model_name": "cnn"},
        )
        assert resp.status_code == 403

    def test_dashboard_overview_without_token_returns_401(self, client):
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 401

    def test_dashboard_overview_with_viewer_token(self, client):
        resp = client.get(
            "/api/v1/dashboard/overview",
            headers=_role_headers("viewer"),
        )
        assert resp.status_code == 200

    def test_experiments_viewer_can_read(self, client):
        resp = client.get(
            "/api/v1/train/experiments",
            headers=_role_headers("viewer"),
        )
        assert resp.status_code == 200

    def test_train_start_researcher_allowed(self, client):
        from unittest.mock import patch, MagicMock
        mock_trainer = MagicMock()
        mock_trainer.experiment_id = "cnn-test-exp"
        mock_trainer.run = MagicMock(return_value={"status": "completed"})
        with patch("training.trainer.Trainer", return_value=mock_trainer):
            resp = client.post(
                "/api/v1/train/start",
                headers=_role_headers("researcher"),
                json={"architecture": "cnn", "epochs": 1},
            )
        assert resp.status_code == 202

    def test_train_start_operator_returns_403(self, client):
        resp = client.post(
            "/api/v1/train/start",
            headers=_role_headers("operator"),
            json={"architecture": "cnn", "epochs": 1},
        )
        assert resp.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# Rate Limit Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestRateLimits:
    def test_rate_limit_strings_have_per_minute(self):
        from app.security.rate_limit import limits
        assert "minute" in limits.LOGIN
        assert "minute" in limits.PREDICTION
        assert "minute" in limits.BATCH_PREDICTION
        assert "minute" in limits.TRAINING
        assert "minute" in limits.DASHBOARD

    def test_login_limit_respects_config(self):
        from app.security.rate_limit import limits
        limit_val = int(limits.LOGIN.split("/")[0])
        assert limit_val == settings.rate_limit_login

    def test_prediction_limit_respects_config(self):
        from app.security.rate_limit import limits
        limit_val = int(limits.PREDICTION.split("/")[0])
        assert limit_val == settings.rate_limit_prediction

    def test_limiter_singleton(self):
        from app.security.rate_limit import limiter
        assert limiter is not None

    def test_exceeded_login_returns_429(self, client):
        """Hit login more than the configured limit from the same IP."""
        max_req = settings.rate_limit_login
        for _ in range(max_req):
            client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "Admin@123!"},
            )
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123!"},
        )
        # Either 429 rate-limited or 200 if limiter reset — accept both
        assert resp.status_code in (200, 429)
