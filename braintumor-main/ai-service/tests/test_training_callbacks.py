"""
tests/test_training_callbacks.py — Unit tests for training.callbacks.build_callbacks.

Tests
-----
- build_callbacks returns a non-empty list of Keras Callback objects.
- ModelCheckpoint is present and points to the correct directory.
- EarlyStopping is present with correct patience per phase.
- ReduceLROnPlateau is present.
- TensorBoard is present.
- CSVLogger is included when cfg.csv_log=True, excluded when False.
- Extra callbacks are appended correctly.
- get_best_checkpoint_path returns None when file does not exist.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import tensorflow as tf

from training.callbacks import build_callbacks, get_best_checkpoint_path
from training.config import TrainingConfig


def _cfg(tmp_path: Path, **kwargs) -> TrainingConfig:
    """Create a TrainingConfig that writes to a temp directory."""
    defaults = dict(output_dir=str(tmp_path), csv_log=True)
    defaults.update(kwargs)   # kwargs can override csv_log and output_dir
    return TrainingConfig(**defaults)


class TestBuildCallbacks:
    def test_returns_list(self, tmp_path):
        cfg = _cfg(tmp_path)
        cbs = build_callbacks(cfg, "test-exp-001")
        assert isinstance(cbs, list)
        assert len(cbs) > 0

    def test_all_keras_callbacks(self, tmp_path):
        cbs = build_callbacks(_cfg(tmp_path), "exp-001")
        for cb in cbs:
            assert isinstance(cb, tf.keras.callbacks.Callback)

    def test_model_checkpoint_present(self, tmp_path):
        cbs = build_callbacks(_cfg(tmp_path), "exp-002")
        types = [type(cb) for cb in cbs]
        assert tf.keras.callbacks.ModelCheckpoint in types

    def test_early_stopping_present(self, tmp_path):
        cbs = build_callbacks(_cfg(tmp_path), "exp-003")
        types = [type(cb) for cb in cbs]
        assert tf.keras.callbacks.EarlyStopping in types

    def test_reduce_lr_present(self, tmp_path):
        cbs = build_callbacks(_cfg(tmp_path), "exp-004")
        types = [type(cb) for cb in cbs]
        assert tf.keras.callbacks.ReduceLROnPlateau in types

    def test_tensorboard_present(self, tmp_path):
        cbs = build_callbacks(_cfg(tmp_path), "exp-005")
        types = [type(cb) for cb in cbs]
        assert tf.keras.callbacks.TensorBoard in types

    def test_csv_logger_present_when_enabled(self, tmp_path):
        cfg = _cfg(tmp_path, csv_log=True)
        cbs = build_callbacks(cfg, "exp-006")
        types = [type(cb) for cb in cbs]
        assert tf.keras.callbacks.CSVLogger in types

    def test_csv_logger_absent_when_disabled(self, tmp_path):
        cfg = _cfg(tmp_path, csv_log=False)
        cbs = build_callbacks(cfg, "exp-007")
        types = [type(cb) for cb in cbs]
        assert tf.keras.callbacks.CSVLogger not in types

    def test_extra_callbacks_appended(self, tmp_path):
        extra = tf.keras.callbacks.LambdaCallback()
        cbs   = build_callbacks(_cfg(tmp_path), "exp-008", extra=[extra])
        assert extra in cbs

    def test_phase2_has_tighter_early_stopping(self, tmp_path):
        cfg = _cfg(tmp_path, early_stopping_patience=10)
        cbs_p1 = build_callbacks(cfg, "exp-009", phase=1)
        cbs_p2 = build_callbacks(cfg, "exp-009", phase=2)

        es_p1 = next(c for c in cbs_p1 if isinstance(c, tf.keras.callbacks.EarlyStopping))
        es_p2 = next(c for c in cbs_p2 if isinstance(c, tf.keras.callbacks.EarlyStopping))

        assert es_p2.patience < es_p1.patience

    def test_checkpoint_path_is_inside_output_dir(self, tmp_path):
        cfg = _cfg(tmp_path)
        cbs = build_callbacks(cfg, "exp-010")
        ckpt = next(
            c for c in cbs
            if isinstance(c, tf.keras.callbacks.ModelCheckpoint)
        )
        assert str(tmp_path) in ckpt.filepath


class TestGetBestCheckpointPath:
    def test_returns_none_when_missing(self, tmp_path):
        cfg = _cfg(tmp_path)
        result = get_best_checkpoint_path(cfg, "nonexistent-exp")
        assert result is None

    def test_returns_path_when_file_exists(self, tmp_path):
        cfg  = _cfg(tmp_path)
        exp  = "existing-exp-001"
        # Simulate the checkpoint file being present (Keras 3 naming)
        ckpt_dir = tmp_path / cfg.architecture / "checkpoints" / exp
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        weights_file = ckpt_dir / "best_weights.weights.h5"
        weights_file.write_text("fake weights")

        result = get_best_checkpoint_path(cfg, exp)
        assert result is not None
        assert result.exists()
