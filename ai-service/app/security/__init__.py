"""
app/security — Production-grade authentication, authorisation, and audit
logging for the Brain Tumour Detection AI Service.

Public surface
--------------
from app.security import (
    # JWT helpers
    create_access_token,
    create_refresh_token,
    decode_token,

    # Password helpers
    hash_password,
    verify_password,

    # User / role types
    Role,
    UserInDB,

    # FastAPI dependencies
    get_current_user,
    require_roles,

    # Audit logging
    audit_logger,
    AuditEvent,
)
"""

from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    is_token_revoked,
)
from app.security.password import hash_password, verify_password
from app.security.roles import Role, Permission, ROLE_PERMISSIONS
from app.security.auth import UserInDB, UserStore, get_user_store
from app.security.dependencies import (
    get_current_user,
    get_current_active_user,
    require_roles,
    optional_auth,
)
from app.security.audit import audit_logger, AuditEvent, log_audit

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "revoke_token",
    "is_token_revoked",
    # Password
    "hash_password",
    "verify_password",
    # Roles
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    # User model
    "UserInDB",
    "UserStore",
    "get_user_store",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_roles",
    "optional_auth",
    # Audit
    "audit_logger",
    "AuditEvent",
    "log_audit",
]
