"""
app/security/dependencies.py — FastAPI dependency functions for authentication
and authorisation.

Usage in route handlers:
    from app.security.dependencies import get_current_user, require_roles

    @router.get("/admin/stuff")
    def admin_only(user = Depends(require_roles(Role.ADMIN))):
        ...

    @router.get("/open-or-auth")
    def mixed(user = Depends(optional_auth)):
        # user is None when unauthenticated
        ...
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError

from app.core.logging import logger
from app.security.auth import UserInDB, authenticate_user, get_user_store
from app.security.jwt import decode_token
from app.security.roles import Permission, Role, get_permissions

# ─── Bearer token extractor ───────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


def _credentials_exception(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# ─── Core user extraction ─────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UserInDB:
    """
    Dependency that extracts and validates the JWT from the Authorization header.

    Returns the full UserInDB record.
    Raises 401 on any failure.
    """
    if credentials is None:
        raise _credentials_exception("No authentication token provided.")

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except ValueError as exc:
        # Token revoked
        raise _credentials_exception(str(exc))
    except JWTError:
        raise _credentials_exception("Token is invalid or has expired.")

    # Validate token type
    if payload.get("type") != "access":
        raise _credentials_exception("Expected an access token.")

    # Resolve user
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise _credentials_exception("Token payload is missing 'sub' claim.")

    store = get_user_store()
    user  = store.get_by_id(user_id)

    if user is None:
        raise _credentials_exception("User associated with this token no longer exists.")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    if user.is_currently_locked():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is temporarily locked until {user.locked_until}.",
        )

    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """
    Thin wrapper that additionally asserts the account is active.
    Prefer this over get_current_user for standard protected routes.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated.",
        )
    return current_user


# ─── Role-based access control ────────────────────────────────────────────────

def require_roles(*allowed_roles: Role):
    """
    Factory that returns a dependency enforcing one of *allowed_roles*.

    Usage:
        @router.post("/train/start")
        def train(user = Depends(require_roles(Role.ADMIN, Role.RESEARCHER))):
            ...
    """
    allowed = set(allowed_roles)

    async def _check(
        current_user: UserInDB = Depends(get_current_active_user),
    ) -> UserInDB:
        if current_user.role not in allowed:
            role_names = ", ".join(r.value for r in sorted(allowed, key=lambda r: r.value))
            logger.warning(
                f"Permission denied: user={current_user.username} "
                f"role={current_user.role.value} required={role_names}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your role '{current_user.role.value}' is not authorised "
                    f"for this action. Required: {role_names}."
                ),
            )
        return current_user

    return _check


def require_permission(permission: Permission):
    """
    Factory that returns a dependency enforcing a specific *permission*.

    Useful when multiple roles should share a finer-grained check.
    """
    async def _check(
        current_user: UserInDB = Depends(get_current_active_user),
    ) -> UserInDB:
        if permission not in get_permissions(current_user.role):
            logger.warning(
                f"Permission denied: user={current_user.username} "
                f"role={current_user.role.value} missing={permission.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission '{permission.value}' is required for this action."
                ),
            )
        return current_user

    return _check


# ─── Optional auth (public endpoints that also accept tokens) ─────────────────

async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[UserInDB]:
    """
    Dependency that returns a UserInDB when a valid token is present,
    or None when no Authorization header is supplied.

    Never raises for missing tokens — only for malformed ones.
    Used for endpoints that are configurable as public or authenticated.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            return None
        store = get_user_store()
        return store.get_by_id(user_id)
    except (JWTError, ValueError):
        return None
