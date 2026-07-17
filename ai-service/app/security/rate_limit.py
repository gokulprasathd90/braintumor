"""
app/security/rate_limit.py — Configurable rate limiting using slowapi.

Provides pre-configured Limiter instance and per-endpoint limit strings.

Usage in route handlers
-----------------------
    from app.security.rate_limit import limiter, limits

    @router.post("/auth/login")
    @limiter.limit(limits.LOGIN)
    async def login(request: Request, ...):
        ...

In main.py, add the SlowAPI middleware and exception handler:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from app.security.rate_limit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
"""

from __future__ import annotations

from fastapi import Request

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


# ─── Key function ─────────────────────────────────────────────────────────────

def _get_key(request: Request) -> str:
    """
    Rate-limit key.  Uses the real client IP, falling back to the direct
    connection's host.  Honours X-Forwarded-For when behind a proxy.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first (left-most) address in the chain
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


# ─── Limiter singleton ────────────────────────────────────────────────────────

limiter = Limiter(key_func=_get_key, default_limits=["1000/hour"])


# ─── Limit strings ────────────────────────────────────────────────────────────

class RateLimits:
    """Pre-computed limit strings drawn from settings."""

    @property
    def LOGIN(self) -> str:
        return f"{settings.rate_limit_login}/minute"

    @property
    def PREDICTION(self) -> str:
        return f"{settings.rate_limit_prediction}/minute"

    @property
    def BATCH_PREDICTION(self) -> str:
        return f"{settings.rate_limit_batch_prediction}/minute"

    @property
    def TRAINING(self) -> str:
        return f"{settings.rate_limit_training}/minute"

    @property
    def DASHBOARD(self) -> str:
        return f"{settings.rate_limit_dashboard}/minute"

    @property
    def AUTH_GENERAL(self) -> str:
        return "30/minute"

    @property
    def REFRESH(self) -> str:
        return "20/minute"


limits = RateLimits()
