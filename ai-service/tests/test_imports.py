"""Tests for third-party and application module imports."""

from __future__ import annotations

import importlib

import pytest

THIRD_PARTY = [
    "fastapi",
    "uvicorn",
    "multipart",
    "tensorflow",
    "keras",
    "cv2",
    "numpy",
    "pandas",
    "matplotlib",
    "sklearn",
    "PIL",
    "tf_explain",
    "dotenv",
    "pydantic",
    "pydantic_settings",
    "loguru",
]

APP_MODULES = [
    "app.core.config",
    "app.core.logging",
    "app.main",
    "app.api.routes",
    "app.models.train",
    "app.models.predict",
    "app.models.evaluate",
    "app.models.load_model",
    "app.models.save_model",
]


@pytest.mark.parametrize("module_name", THIRD_PARTY)
def test_third_party_import(module_name: str) -> None:
    importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", APP_MODULES)
def test_app_module_import(module_name: str) -> None:
    importlib.import_module(module_name)
