"""
app/security/roles.py — Role and permission definitions.

Role hierarchy (highest → lowest privilege):
  Admin      — full access to every endpoint
  Researcher — training, experiments, Grad-CAM, metrics
  Operator   — prediction, preprocessing, model selection
  Viewer     — dashboard and experiment read-only access

Every role also inherits the permissions of roles below it in the hierarchy.
"""

from __future__ import annotations

from enum import Enum


# ─── Roles ────────────────────────────────────────────────────────────────────

class Role(str, Enum):
    ADMIN      = "admin"
    RESEARCHER = "researcher"
    OPERATOR   = "operator"
    VIEWER     = "viewer"


# ─── Fine-grained permissions ─────────────────────────────────────────────────

class Permission(str, Enum):
    # Model management
    MODEL_READ     = "model:read"
    MODEL_RELOAD   = "model:reload"
    MODEL_MANAGE   = "model:manage"

    # Training
    TRAIN_START    = "train:start"
    TRAIN_READ     = "train:read"

    # Dataset
    DATASET_READ      = "dataset:read"
    DATASET_PREPARE   = "dataset:prepare"
    DATASET_MANAGE    = "dataset:manage"

    # Prediction / inference
    PREDICT_SINGLE = "predict:single"
    PREDICT_BATCH  = "predict:batch"

    # Preprocessing
    PREPROCESS     = "preprocess:run"

    # Grad-CAM
    GRADCAM        = "gradcam:generate"

    # Metrics / dashboard
    METRICS_READ   = "metrics:read"
    DASHBOARD_READ = "dashboard:read"
    DASHBOARD_ADMIN = "dashboard:admin"

    # Experiments
    EXPERIMENT_READ   = "experiment:read"
    EXPERIMENT_WRITE  = "experiment:write"

    # User / admin management
    USER_MANAGE    = "user:manage"

    # Audit logs
    AUDIT_READ     = "audit:read"


# ─── Role → permission mapping ────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.DASHBOARD_READ,
        Permission.METRICS_READ,
        Permission.EXPERIMENT_READ,
        Permission.MODEL_READ,
    },
    Role.OPERATOR: {
        Permission.PREDICT_SINGLE,
        Permission.PREDICT_BATCH,
        Permission.PREPROCESS,
        Permission.MODEL_READ,
        Permission.MODEL_RELOAD,
        Permission.DASHBOARD_READ,
        Permission.METRICS_READ,
        Permission.EXPERIMENT_READ,
    },
    Role.RESEARCHER: {
        Permission.TRAIN_START,
        Permission.TRAIN_READ,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_WRITE,
        Permission.GRADCAM,
        Permission.METRICS_READ,
        Permission.DASHBOARD_READ,
        Permission.MODEL_READ,
        Permission.DATASET_READ,
        Permission.PREDICT_SINGLE,
        Permission.PREDICT_BATCH,
        Permission.PREPROCESS,
    },
    Role.ADMIN: set(Permission),  # all permissions
}


def get_permissions(role: Role) -> set[Permission]:
    """Return the complete set of permissions for *role*."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Return True if *role* holds *permission*."""
    return permission in get_permissions(role)


# ─── Endpoint-to-role requirements map ───────────────────────────────────────
# Used for documentation and enforced via require_roles() dependency.

ENDPOINT_ROLES: dict[str, list[Role]] = {
    # Model management
    "models:list":   [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR, Role.VIEWER],
    "models:reload": [Role.ADMIN, Role.OPERATOR],
    "models:manage": [Role.ADMIN],

    # Training
    "train:start":   [Role.ADMIN, Role.RESEARCHER],
    "train:read":    [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR],

    # Dataset
    "dataset:read":    [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR, Role.VIEWER],
    "dataset:prepare": [Role.ADMIN, Role.RESEARCHER],
    "dataset:manage":  [Role.ADMIN],

    # Prediction
    "predict:single": [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR],
    "predict:batch":  [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR],

    # Dashboard
    "dashboard:read":  [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR, Role.VIEWER],
    "dashboard:admin": [Role.ADMIN],

    # Experiments
    "experiments:read":  [Role.ADMIN, Role.RESEARCHER, Role.OPERATOR, Role.VIEWER],
    "experiments:write": [Role.ADMIN, Role.RESEARCHER],

    # User management (admin only)
    "users:manage": [Role.ADMIN],
}
