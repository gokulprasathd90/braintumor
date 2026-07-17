"""
app/security/audit.py — Structured audit logging for security-relevant events.

All audit records are written to a rotating JSONL file:
  logs/audit/audit_YYYY-MM-DD.jsonl

Each line is a self-contained JSON object.  The audit log is separate from
the application log so it can be shipped to a SIEM without noise.

Usage
-----
    from app.security.audit import log_audit, AuditEvent

    log_audit(
        AuditEvent.LOGIN,
        username="alice",
        request_ip="192.168.1.10",
        details={"role": "researcher"},
    )
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import logger


# ─── Event catalogue ─────────────────────────────────────────────────────────

class AuditEvent(str, Enum):
    # Authentication
    LOGIN              = "auth.login"
    LOGOUT             = "auth.logout"
    LOGIN_FAILED       = "auth.login_failed"
    TOKEN_REFRESH      = "auth.token_refresh"
    TOKEN_REVOKED      = "auth.token_revoked"
    PASSWORD_RESET     = "auth.password_reset"
    ACCOUNT_LOCKED     = "auth.account_locked"

    # Authorisation
    PERMISSION_DENIED  = "authz.permission_denied"

    # Model management
    MODEL_RELOAD       = "model.reload"
    MODEL_LOADED       = "model.loaded"

    # Training
    TRAIN_START        = "train.start"
    TRAIN_COMPLETE     = "train.complete"
    TRAIN_FAILED       = "train.failed"

    # Dataset
    DATASET_PREPARE    = "dataset.prepare"
    DATASET_VALIDATE   = "dataset.validate"

    # Inference
    PREDICT_SINGLE     = "predict.single"
    PREDICT_BATCH      = "predict.batch"

    # Admin actions
    USER_CREATED       = "admin.user_created"
    USER_DEACTIVATED   = "admin.user_deactivated"
    USER_UNLOCKED      = "admin.user_unlocked"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"


# ─── Audit record ─────────────────────────────────────────────────────────────

class AuditRecord:
    """Immutable structured audit record."""

    __slots__ = (
        "timestamp", "event", "username", "user_id",
        "request_ip", "endpoint", "outcome", "details",
    )

    def __init__(
        self,
        event:      AuditEvent,
        username:   Optional[str]          = None,
        user_id:    Optional[str]          = None,
        request_ip: Optional[str]          = None,
        endpoint:   Optional[str]          = None,
        outcome:    str                    = "success",
        details:    Optional[dict[str, Any]] = None,
    ) -> None:
        self.timestamp  = datetime.now(timezone.utc).isoformat()
        self.event      = event.value
        self.username   = username
        self.user_id    = user_id
        self.request_ip = request_ip
        self.endpoint   = endpoint
        self.outcome    = outcome
        self.details    = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp":  self.timestamp,
            "event":      self.event,
            "username":   self.username,
            "user_id":    self.user_id,
            "request_ip": self.request_ip,
            "endpoint":   self.endpoint,
            "outcome":    self.outcome,
            "details":    self.details,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


# ─── Audit logger ─────────────────────────────────────────────────────────────

class AuditLogger:
    """
    Thread-safe rotating JSONL audit logger.

    Writes one JSON object per line to logs/audit/audit_YYYY-MM-DD.jsonl.
    The file is rotated automatically when the date changes.
    """

    def __init__(self, audit_dir: Path) -> None:
        self._dir  = audit_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._date: Optional[str] = None
        self._fh: Optional[Any]   = None

    def _rotate_if_needed(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._date:
            if self._fh:
                self._fh.close()
            self._date = today
            log_path   = self._dir / f"audit_{today}.jsonl"
            self._fh   = open(log_path, "a", encoding="utf-8", buffering=1)

    def write(self, record: AuditRecord) -> None:
        with self._lock:
            self._rotate_if_needed()
            if self._fh:
                self._fh.write(record.to_json() + "\n")

    def close(self) -> None:
        with self._lock:
            if self._fh:
                self._fh.close()
                self._fh = None


# ─── Singleton logger instance ────────────────────────────────────────────────

audit_logger = AuditLogger(settings.audit_log_dir)


# ─── Convenience function ─────────────────────────────────────────────────────

def log_audit(
    event:      AuditEvent,
    username:   Optional[str]            = None,
    user_id:    Optional[str]            = None,
    request_ip: Optional[str]            = None,
    endpoint:   Optional[str]            = None,
    outcome:    str                      = "success",
    details:    Optional[dict[str, Any]] = None,
) -> None:
    """
    Create an AuditRecord and write it to the rotating JSONL file.

    Also mirrors the record to the standard application logger at DEBUG level
    so audit events appear in the main log during development.
    """
    record = AuditRecord(
        event=event,
        username=username,
        user_id=user_id,
        request_ip=request_ip,
        endpoint=endpoint,
        outcome=outcome,
        details=details,
    )
    audit_logger.write(record)
    logger.debug(
        f"AUDIT | {record.event} | user={record.username} "
        f"outcome={record.outcome}"
    )
