"""
app/training/__init__.py — Public surface of the app.training package.

Re-exports the primary symbols from the ``training`` package so that
application code can use the shorter ``app.training`` import path.

    from app.training import Trainer, TrainingConfig, train
    from app.training import Experiment, ExperimentRegistry
    from app.training import build_callbacks, TrainingJobStore
"""

from training.callbacks import build_callbacks
from training.checkpoints import (
    checkpoint_dir,
    delete_checkpoint,
    list_checkpoints,
    load_best_weights,
    load_checkpoint_info,
    save_checkpoint_info,
)
from training.config import DEFAULT_TRAINING_CONFIG, TrainingConfig
from training.experiment import Experiment, ExperimentRegistry
from training.trainer import Trainer, train
from app.training.job_store import TrainingJobStore

__all__ = [
    # Core training
    "Trainer",
    "train",
    "TrainingConfig",
    "DEFAULT_TRAINING_CONFIG",
    # Experiment tracking
    "Experiment",
    "ExperimentRegistry",
    # Callbacks
    "build_callbacks",
    # Checkpoint utilities
    "checkpoint_dir",
    "save_checkpoint_info",
    "load_best_weights",
    "load_checkpoint_info",
    "list_checkpoints",
    "delete_checkpoint",
    # Async job management
    "TrainingJobStore",
]
