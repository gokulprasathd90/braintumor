"""
app/security/jwt.py — JWT creation, validation, and revocation.

Supports two token types:
  access  — short-lived bearer token (default 30 min)
  refresh — long-lived token for obtaining new access tokens (default 7 days)

Token revocation is implemented via an in-memory revocation set.  For
production deployments with multiple processes, replace the in-memory set
with a Redis-backed store (same interface).

Functions
---------
create_access_token(data, expires_delta) -> str
create_refresh_token(data, expires_delta) -> str
decode_token(token) -> dict
revoke_token(jti) -> None
is_token_revoked(jti) -> bool
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import logger

# ─── Constants ────────────────────────────────────────────────────────────────

TOKEN_TYPE_ACCESS  = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ─── In-memory revocation store ───────────────────────────────────────────────
# jti (JWT ID) → expiry timestamp (UTC).  Tokens past their expiry are pruned
# from the set on the next add operation.

_revoked_tokens: dict[str, datetime] = {}


def _prune_expired() -> None:
    """Remove tokens that have naturally expired (no longer a security risk)."""
    now = datetime.now(timezone.utc)
    expired_keys = [jti for jti, exp in _revoked_tokens.items() if exp < now]
    for k in expired_keys:
        del _revoked_tokens[k]


# ─── Token creation ───────────────────────────────────────────────────────────

def _build_token(
    data: dict[str, Any],
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """
    Build and sign a JWT with the given payload and expiry.

    Always injects:
      iat  — issued-at timestamp
      exp  — expiry timestamp
      jti  — unique token ID (for revocation)
      type — "access" | "refresh"
    """
    now    = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        **data,
        "iat":  now,
        "exp":  expire,
        "jti":  str(uuid.uuid4()),
        "type": token_type,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a short-lived access token.

    Parameters
    ----------
    data
        Payload to embed.  Typically ``{"sub": user_id, "role": role}``.
    expires_delta
        Override the default expiry from settings.
    """
    delta = expires_delta or timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return _build_token(data, TOKEN_TYPE_ACCESS, delta)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a long-lived refresh token.

    Only the ``sub`` claim is typically needed here; roles are not
    embedded so stale roles cannot be refreshed without re-login.
    """
    delta = expires_delta or timedelta(
        days=settings.refresh_token_expire_days
    )
    return _build_token(data, TOKEN_TYPE_REFRESH, delta)


# ─── Token decoding / validation ─────────────────────────────────────────────

def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate *token*.  Returns the payload dict on success.

    Raises
    ------
    JWTError
        If the token is expired, tampered with, or otherwise invalid.
    ValueError
        If the token has been revoked.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        logger.debug(f"JWT decode failed: {exc}")
        raise

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise ValueError(f"Token has been revoked (jti={jti})")

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token specifically.

    Enforces that the ``type`` claim equals ``"refresh"``.
    """
    payload = decode_token(token)
    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise ValueError("Token is not a refresh token.")
    return payload


# ─── Revocation ───────────────────────────────────────────────────────────────

def revoke_token(jti: str, expires_at: datetime | None = None) -> None:
    """
    Add *jti* to the revocation set.

    Parameters
    ----------
    jti
        The ``jti`` claim from the token payload.
    expires_at
        The token's ``exp`` value.  If omitted a far-future sentinel is used.
    """
    _prune_expired()
    exp = expires_at or datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days + 1
    )
    _revoked_tokens[jti] = exp
    logger.debug(f"Token revoked: jti={jti}")


def is_token_revoked(jti: str) -> bool:
    """Return True if *jti* is in the revocation set."""
    if jti not in _revoked_tokens:
        return False
    # Check if the entry itself has expired (clean up lazily)
    if _revoked_tokens[jti] < datetime.now(timezone.utc):
        del _revoked_tokens[jti]
        return False
    return True


def revocation_store_size() -> int:
    """Return the current size of the revocation set (for monitoring)."""
    _prune_expired()
    return len(_revoked_tokens)
