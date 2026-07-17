import pytest
import os
from fastapi.testclient import TestClient

# Ensure test environment variables are set before importing the app
os.environ["AI_SERVICE_ENV"] = "test"
os.environ["BCRYPT_ROUNDS"] = "4"

from app.main import app
from app.security.dependencies import get_current_user, get_current_active_user, optional_auth
from app.security.auth import UserInDB
from app.security.roles import Role

# A mock administrator user to bypass authentication checks
MOCK_USER = UserInDB(
    user_id="mock-admin-id",
    username="admin",
    email="admin@test.local",
    hashed_password="",
    role=Role.ADMIN,
    is_active=True,
    is_locked=False,
    failed_login_count=0,
    locked_until=None
)

@pytest.fixture(autouse=True)
def configure_auth_overrides(request):
    """
    Bypasses authentication/authorization for all tests EXCEPT those in test_security.py.
    This ensures existing tests do not fail due to missing tokens.
    """
    if "test_security.py" in request.node.fspath.strpath or "unauthenticated" in request.node.name:
        app.dependency_overrides.clear()
        yield
        app.dependency_overrides.clear()
        return

    # Mock user providers
    async def mock_get_current_user():
        return MOCK_USER

    async def mock_get_current_active_user():
        return MOCK_USER

    async def mock_optional_auth():
        return MOCK_USER

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[optional_auth] = mock_optional_auth

    yield

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def configure_limiter(request):
    """
    Disables the rate limiter for all tests except for the one testing rate limits.
    This avoids 429 errors from failing the test suite during rapid iterations.
    """
    from app.security.rate_limit import limiter
    
    # Enable rate limiting only for the specific test that asserts 429 behavior
    if "test_exceeded_login_returns_429" in request.node.name:
        limiter.enabled = True
    else:
        limiter.enabled = False

    yield
