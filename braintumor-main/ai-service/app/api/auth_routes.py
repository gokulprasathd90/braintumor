"""
app/api/auth_routes.py — Authentication REST endpoints.

Endpoints
---------
POST /auth/login        Login with username + password, receive token pair.
POST /auth/logout       Revoke the current access and refresh tokens.
POST /auth/refresh      Exchange a refresh token for a new access token.
GET  /auth/me           Return the current authenticated user's profile.
POST /auth/change-password  Change the authenticated user's password.
GET  /auth/users        (Admin) List all users.
POST /auth/users        (Admin) Create a new user.
POST /auth/users/{user_id}/unlock   (Admin) Unlock a locked account.
"""


from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.core.logging import logger
from app.security.audit import AuditEvent, log_audit
from app.security.auth import UserInDB, authenticate_user, get_user_store
from app.security.dependencies import (
    get_current_active_user,
    require_roles,
)
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    revoke_token,
)
from app.security.password import (
    generate_reset_token,
    validate_password_strength,
)
from app.security.rate_limit import limiter, limits
from app.security.roles import Role

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

_bearer = HTTPBearer(auto_error=False)


# ─── Request / Response schemas ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int        # seconds until access token expires
    user:          Dict[str, Any]


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int


class MessageResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password:     str = Field(..., min_length=8)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email:    str = Field(..., min_length=5, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)
    role:     Role = Role.VIEWER


class UserListResponse(BaseModel):
    users: List[Dict[str, Any]]
    total: int


# ─── POST /auth/login ─────────────────────────────────────────────────────────

@auth_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and obtain JWT token pair",
)
@limiter.limit(limits.LOGIN)
async def login(
    request: Request,
    body: LoginRequest,
) -> TokenResponse:
    """
    Authenticate with *username* and *password*.

    Returns a short-lived access token and a long-lived refresh token.
    Apply account lockout after `settings.max_failed_logins` consecutive
    failures.

    **Rate limit**: 5 requests / minute per IP.
    """
    ip = request.client.host if request.client else "unknown"
    user = authenticate_user(body.username, body.password)

    if user is None:
        log_audit(
            AuditEvent.LOGIN_FAILED,
            username=body.username,
            request_ip=ip,
            endpoint="/auth/login",
            outcome="failure",
            details={"reason": "invalid credentials or locked account"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Build tokens
    token_data = {"sub": user.user_id, "role": user.role.value}
    access_token  = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": user.user_id})

    log_audit(
        AuditEvent.LOGIN,
        username=user.username,
        user_id=user.user_id,
        request_ip=ip,
        endpoint="/auth/login",
        outcome="success",
        details={"role": user.role.value},
    )

    expires_in = settings.access_token_expire_minutes * 60
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=user.to_public().to_dict(),
    )


# ─── POST /auth/logout ────────────────────────────────────────────────────────

@auth_router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout and revoke tokens",
)
@limiter.limit(limits.AUTH_GENERAL)
async def logout(
    request: Request,
    body: Optional[RefreshRequest] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    current_user: UserInDB = Depends(get_current_active_user),
) -> MessageResponse:
    """
    Revoke the current access token (and optionally the refresh token).

    The body is optional — send ``{"refresh_token": "..."}`` to also revoke
    the refresh token in the same call.
    """
    ip = request.client.host if request.client else "unknown"

    # Revoke access token
    if credentials:
        try:
            payload = __import__(
                "jose.jwt", fromlist=["decode"]
            ).decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            jti = payload.get("jti")
            if jti:
                exp_ts = payload.get("exp")
                exp_dt = (
                    datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                    if exp_ts
                    else None
                )
                revoke_token(jti, exp_dt)
        except Exception:
            pass  # Already expired — revocation is a no-op

    # Revoke refresh token if provided
    if body and body.refresh_token:
        try:
            rp = decode_refresh_token(body.refresh_token)
            rjti = rp.get("jti")
            if rjti:
                exp_ts = rp.get("exp")
                exp_dt = (
                    datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                    if exp_ts
                    else None
                )
                revoke_token(rjti, exp_dt)
        except Exception:
            pass

    log_audit(
        AuditEvent.LOGOUT,
        username=current_user.username,
        user_id=current_user.user_id,
        request_ip=ip,
        endpoint="/auth/logout",
        outcome="success",
    )

    return MessageResponse(message="Logged out successfully.")


# ─── POST /auth/refresh ───────────────────────────────────────────────────────

@auth_router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token",
)
@limiter.limit(limits.REFRESH)
async def refresh_token_endpoint(
    request: Request,
    body: RefreshRequest,
) -> AccessTokenResponse:
    """
    Exchange a valid refresh token for a new access token.

    The refresh token is **not** invalidated so it can be reused until it
    naturally expires.  Call ``POST /auth/logout`` to explicitly revoke it.
    """
    ip = request.client.host if request.client else "unknown"

    try:
        payload = decode_refresh_token(body.refresh_token)
    except (JWTError, ValueError) as exc:
        log_audit(
            AuditEvent.TOKEN_REFRESH,
            request_ip=ip,
            endpoint="/auth/refresh",
            outcome="failure",
            details={"reason": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing 'sub' claim.",
        )

    store = get_user_store()
    user  = store.get_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists or is inactive.",
        )

    new_access = create_access_token({"sub": user.user_id, "role": user.role.value})

    log_audit(
        AuditEvent.TOKEN_REFRESH,
        username=user.username,
        user_id=user.user_id,
        request_ip=ip,
        endpoint="/auth/refresh",
        outcome="success",
    )

    return AccessTokenResponse(
        access_token=new_access,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ─── GET /auth/me ─────────────────────────────────────────────────────────────

@auth_router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def get_me(
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Return the authenticated user's public profile."""
    return {"success": True, "data": current_user.to_public().to_dict()}


# ─── POST /auth/change-password ───────────────────────────────────────────────

@auth_router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change the authenticated user's password",
)
@limiter.limit(limits.AUTH_GENERAL)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: UserInDB = Depends(get_current_active_user),
) -> MessageResponse:
    """Verify the current password then apply the new one."""
    from app.security.password import verify_password as _vp

    ip = request.client.host if request.client else "unknown"

    if not _vp(body.current_password, current_user.hashed_password):
        log_audit(
            AuditEvent.PASSWORD_RESET,
            username=current_user.username,
            user_id=current_user.user_id,
            request_ip=ip,
            endpoint="/auth/change-password",
            outcome="failure",
            details={"reason": "current password incorrect"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    errors = validate_password_strength(body.new_password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Password is too weak.", "errors": errors},
        )

    store = get_user_store()
    store.update_password(current_user.user_id, body.new_password)

    log_audit(
        AuditEvent.PASSWORD_RESET,
        username=current_user.username,
        user_id=current_user.user_id,
        request_ip=ip,
        endpoint="/auth/change-password",
        outcome="success",
    )

    return MessageResponse(message="Password changed successfully.")


# ─── GET /auth/users (Admin) ──────────────────────────────────────────────────

@auth_router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] List all users",
)
async def list_users(
    _: UserInDB = Depends(require_roles(Role.ADMIN)),
) -> UserListResponse:
    """Admin-only: return all user accounts."""
    store = get_user_store()
    users = store.list_users()
    return UserListResponse(
        users=[u.to_dict() for u in users],
        total=len(users),
    )


# ─── POST /auth/users (Admin) ─────────────────────────────────────────────────

@auth_router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a new user",
)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    admin: UserInDB = Depends(require_roles(Role.ADMIN)),
) -> Dict[str, Any]:
    """Admin-only: create a new user account."""
    ip = request.client.host if request.client else "unknown"

    errors = validate_password_strength(body.password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Password is too weak.", "errors": errors},
        )

    store = get_user_store()
    try:
        new_user = store.create_user(
            username=body.username,
            email=body.email,
            plain_password=body.password,
            role=body.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    log_audit(
        AuditEvent.USER_CREATED,
        username=admin.username,
        user_id=admin.user_id,
        request_ip=ip,
        endpoint="/auth/users",
        outcome="success",
        details={"new_user": body.username, "role": body.role.value},
    )

    return {"success": True, "data": new_user.to_public().to_dict()}


# ─── POST /auth/users/{user_id}/unlock (Admin) ────────────────────────────────

@auth_router.post(
    "/users/{user_id}/unlock",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Unlock a locked user account",
)
async def unlock_user(
    user_id: str,
    request: Request,
    admin: UserInDB = Depends(require_roles(Role.ADMIN)),
) -> MessageResponse:
    """Admin-only: clear the lockout on a specific account."""
    ip = request.client.host if request.client else "unknown"
    store = get_user_store()

    target = store.get_by_id(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    store.unlock_user(user_id)

    log_audit(
        AuditEvent.USER_UNLOCKED,
        username=admin.username,
        user_id=admin.user_id,
        request_ip=ip,
        endpoint=f"/auth/users/{user_id}/unlock",
        outcome="success",
        details={"unlocked_user": target.username},
    )

    return MessageResponse(message=f"Account '{target.username}' has been unlocked.")
