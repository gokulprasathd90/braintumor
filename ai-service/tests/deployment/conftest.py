"""
tests/deployment/conftest.py
──────────────────────────────
Conftest for deployment validation tests.

These tests inspect configuration files on disk — they do not start the
FastAPI application or hit any HTTP endpoints.  We override the parent
conftest's autouse auth and rate-limiter fixtures so they don't fire
(and don't try to import the app for tests that don't need it).
"""

import pytest


@pytest.fixture(autouse=True)
def configure_auth_overrides(request):
    """
    No-op override: deployment tests don't use the FastAPI test client.
    Overrides the same-named autouse fixture in the parent conftest.py so
    that the parent fixture's app.dependency_overrides logic is never reached
    for tests in this package.
    """
    yield


@pytest.fixture(autouse=True)
def configure_limiter(request):
    """
    No-op override: deployment tests don't exercise rate-limited endpoints.
    """
    yield
