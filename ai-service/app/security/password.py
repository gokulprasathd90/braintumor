"""
app/security/password.py — bcrypt-based password hashing and verification.

Uses passlib's CryptContext which handles algorithm versioning, salting,
and upgrading hashes transparently.

Functions
---------
hash_password(plain: str) -> str
    Hash a plaintext password with bcrypt.

verify_password(plain: str, hashed: str) -> bool
    Return True if *plain* matches the bcrypt *hashed* value.

generate_reset_token() -> str
    Generate a cryptographically-secure URL-safe token for password resets.
"""

from __future__ import annotations

import secrets
import string

from passlib.context import CryptContext

from app.core.config import settings

# ─── CryptContext ─────────────────────────────────────────────────────────────
# Using bcrypt as the default scheme.  The `rounds` parameter is taken from
# settings so tests can lower it (e.g. BCRYPT_ROUNDS=4) without compromising
# security in production.

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)


# ─── Public API ───────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash *plain* with bcrypt and return the hash string.

    The returned hash is self-contained (algorithm + rounds + salt + digest)
    and is safe to store directly in a database column.

    Raises
    ------
    ValueError
        If *plain* is empty.
    """
    if not plain:
        raise ValueError("Password must not be empty.")
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if *plain* matches the bcrypt *hashed* value.

    Uses a constant-time comparison internally to prevent timing attacks.
    Returns False (never raises) for any mismatch or malformed hash.
    """
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    """
    Return True if *hashed* was produced with outdated parameters
    (e.g. fewer rounds) and should be re-hashed at next login.
    """
    try:
        return _pwd_context.needs_update(hashed)
    except Exception:
        return False


def generate_reset_token(length: int = 48) -> str:
    """
    Return a URL-safe, cryptographically-random token for password resets.

    The token is Base-64-alphabet safe (no ``+``, ``/``, ``=``) so it can be
    embedded directly in a URL query-string without further encoding.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def validate_password_strength(password: str) -> list[str]:
    """
    Return a list of failing rule descriptions (empty = strong enough).

    Rules:
    - At least 8 characters.
    - Contains at least one uppercase letter.
    - Contains at least one digit.
    - Contains at least one special character.
    """
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit.")
    if not any(c in string.punctuation for c in password):
        errors.append("Password must contain at least one special character.")
    return errors
