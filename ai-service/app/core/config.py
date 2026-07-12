"""
config.py — Centralised configuration for the AI service.

All settings are read from environment variables (or a .env file via
python-dotenv).  Pydantic-Settings validates types and provides defaults.
Import the singleton `settings` anywhere in the app:

    from app.core.config import settings
    print(settings.image_size)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Resolve the project root (ai-service/) relative to this file ─────────────
BASE_DIR = Path(__file__).resolve().parents[2]   # ai-service/


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    ai_service_host: str  = "0.0.0.0"
    ai_service_port: int  = 8000
    ai_service_env:  str  = "development"
    ai_service_debug: bool = True

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000,http://localhost:5000"

    @property
    def cors_origins(self) -> List[str]:
        """Return allowed origins as a parsed list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── Model paths ───────────────────────────────────────────────────────────
    saved_models_dir: Path = BASE_DIR / "saved_models"
    active_model: str      = "efficientnet"   # cnn | vgg16 | resnet50 | efficientnet

    @property
    def active_model_path(self) -> Path:
        """Absolute path to the currently active model directory."""
        return self.saved_models_dir / self.active_model

    # ── Image settings ────────────────────────────────────────────────────────
    image_size: int      = 224   # target width = height (pixels)
    image_channels: int  = 3

    @property
    def input_shape(self) -> tuple:
        """Keras-style input shape (H, W, C)."""
        return (self.image_size, self.image_size, self.image_channels)

    # ── Classification classes ─────────────────────────────────────────────
    class_names: str = "glioma,meningioma,notumor,pituitary"

    @property
    def classes(self) -> List[str]:
        """Return class names as a parsed list."""
        return [c.strip() for c in self.class_names.split(",") if c.strip()]

    @property
    def num_classes(self) -> int:
        return len(self.classes)

    # ── Dataset paths ─────────────────────────────────────────────────────────
    dataset_raw_dir: Path      = BASE_DIR / "dataset" / "raw"
    dataset_processed_dir: Path = BASE_DIR / "dataset" / "processed"

    # ── Grad-CAM output ───────────────────────────────────────────────────────
    gradcam_output_dir: Path = BASE_DIR / "gradcam_output"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_dir: Path  = BASE_DIR / "logs"

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("active_model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        allowed = {"cnn", "vgg16", "resnet50", "efficientnet"}
        if v.lower() not in allowed:
            raise ValueError(f"active_model must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("ai_service_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "production", "test"}
        if v.lower() not in allowed:
            raise ValueError(f"ai_service_env must be one of {allowed}")
        return v.lower()


# ── Singleton ─────────────────────────────────────────────────────────────────
settings = Settings()

# Ensure required directories exist at import time
settings.saved_models_dir.mkdir(parents=True, exist_ok=True)
settings.log_dir.mkdir(parents=True, exist_ok=True)
settings.dataset_raw_dir.mkdir(parents=True, exist_ok=True)
settings.dataset_processed_dir.mkdir(parents=True, exist_ok=True)
settings.gradcam_output_dir.mkdir(parents=True, exist_ok=True)
