"""
training/trainer.py — High-level Trainer class for the full training pipeline.

The ``Trainer`` orchestrates every step in one cohesive object:

    1. Load (or build fresh) train / val / test data generators.
    2. Build a compiled Keras model via ``app.models.architectures.build_model``.
    3. Run Phase-1 training (frozen backbone, head only).
    4. Optionally run Phase-2 fine-tuning (unfrozen top-N backbone layers).
    5. Save best checkpoint weights and the final model artefact.
    6. Evaluate the model against the test split.
    7. Persist experiment metadata to disk via ``ExperimentRegistry``.

Directory layout produced
--------------------------
    <output_dir>/
        <architecture>/
            saved_model.pb  (TF SavedModel)
            <architecture>.h5
            model_info.json
            checkpoints/
                <experiment_id>/
                    best_weights.h5
                    checkpoint_info.json
    <log_dir>/
        experiments/
            experiment_registry.json
            <experiment_id>/
                experiment.json
                training_config.json
        tensorboard/<experiment_id>/phase1/
        tensorboard/<experiment_id>/phase2/
        training/<experiment_id>_phase1.csv
        training/<experiment_id>_phase2.csv

CLI usage
---------
    python -m training.trainer --architecture efficientnet --epochs 20
    python -m training.trainer --architecture resnet50 --epochs 30 --batch-size 16

Python usage
------------
    from training.config import TrainingConfig
    from training.trainer import Trainer

    cfg     = TrainingConfig(architecture="efficientnet", epochs=20)
    trainer = Trainer(cfg)
    result  = trainer.run()
    print(result["experiment_id"], result["best_val_accuracy"])
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, Optional

import tensorflow as tf

from app.core.config import settings
from app.core.logging import logger
from app.models.architectures import build_model, unfreeze_top_layers
from app.models.evaluate import evaluate_model
from app.models.save_model import save_keras_model
from app.preprocessing.augmentation import AugmentationConfig
from app.preprocessing.preprocess import build_generators, build_test_generator
from training.callbacks import build_callbacks
from training.checkpoints import save_checkpoint_info
from training.config import TrainingConfig
from training.experiment import Experiment, ExperimentRegistry


# ─────────────────────────────────────────────────────────────────────────────
# Trainer
# ─────────────────────────────────────────────────────────────────────────────

class Trainer:
    """
    Orchestrates the full two-phase transfer-learning training pipeline.

    Parameters
    ----------
    cfg : TrainingConfig
        Complete training configuration.
    aug_cfg : AugmentationConfig | None
        Augmentation configuration for the training generator.
        Defaults to ``AugmentationConfig()`` (MRI-tuned defaults).
    experiments_dir : Path | None
        Override where experiment metadata is persisted.
        Defaults to ``settings.log_dir / "experiments"``.

    Attributes
    ----------
    experiment : Experiment
        Created on ``Trainer.__init__``; updated and saved throughout the run.
    model : tf.keras.Model | None
        Populated after ``_build_model()`` is called.
    """

    def __init__(
        self,
        cfg: TrainingConfig,
        *,
        aug_cfg: Optional[AugmentationConfig] = None,
        experiments_dir: Optional[Path] = None,
    ) -> None:
        self.cfg = cfg
        self.aug_cfg = aug_cfg or AugmentationConfig()
        self.model: Optional[tf.keras.Model] = None

        # Create the experiment record immediately so callers can reference
        # the experiment_id before training begins (e.g. job polling).
        self.experiment = Experiment.create(
            cfg,
            experiments_dir=experiments_dir,
        )
        self.experiment.save()
        logger.info(
            f"Trainer initialised | experiment_id={self.experiment.experiment_id} "
            f"architecture={cfg.architecture} epochs={cfg.epochs}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def experiment_id(self) -> str:
        return self.experiment.experiment_id

    def run(self) -> Dict[str, Any]:
        """
        Execute the full training pipeline and return a result summary.

        Returns
        -------
        dict
            {
              "experiment_id":       str,
              "architecture":        str,
              "epochs_phase1":       int,
              "epochs_phase2":       int,
              "best_val_accuracy":   float | None,
              "final_val_loss":      float | None,
              "training_duration_s": float,
              "eval_metrics":        dict,
              "model_paths":         dict,
              "status":              str,
            }

        Raises
        ------
        Exception
            Any exception from the underlying training loop is re-raised after
            the experiment record is marked as "failed".
        """
        self.experiment.update_status("running")
        self.experiment.save()
        t0 = time.perf_counter()

        try:
            # 1. Data generators
            train_gen, val_gen = self._build_generators()

            # 2. Compile model
            self._build_model()

            # 3. Phase 1 — train classification head
            history_p1 = self._train_phase1(train_gen, val_gen)

            # 4. Phase 2 — fine-tune backbone (optional)
            history_p2 = self._train_phase2(train_gen, val_gen)

            # 5. Save final model
            model_paths = self._save_final_model()

            # 6. Evaluate on test split
            eval_metrics = self._evaluate(model_paths)

            # 7. Finalise experiment record
            duration_s = time.perf_counter() - t0
            self.experiment.set_duration(duration_s)
            self.experiment.update_status("completed")
            self.experiment.record_model_paths(model_paths)
            self.experiment.save()

            logger.info(
                f"Training complete | experiment={self.experiment_id} "
                f"duration={duration_s:.1f}s "
                f"best_val_accuracy={self.experiment.best_val_accuracy}"
            )

        except Exception as exc:
            duration_s = time.perf_counter() - t0
            self.experiment.set_duration(duration_s)
            self.experiment.record_error(exc)
            self.experiment.save()
            logger.exception(
                f"Training failed | experiment={self.experiment_id} "
                f"error={exc}"
            )
            raise

        return self._build_result_summary()

    # ─────────────────────────────────────────────────────────────────────────
    # Internal steps
    # ─────────────────────────────────────────────────────────────────────────

    def _build_generators(self):
        """Build train and val generators from the processed dataset directory."""
        processed_dir = self.cfg.resolved_dataset_dir

        if not processed_dir.exists():
            raise FileNotFoundError(
                f"Dataset directory not found: {processed_dir}. "
                "Run POST /api/v1/dataset/prepare first."
            )

        train_gen, val_gen = build_generators(
            processed_dir,
            batch_size=self.cfg.batch_size,
            aug_cfg=self.aug_cfg,
            seed=self.cfg.seed,
        )

        # Record dataset provenance in the experiment
        gen_class_map: Dict[str, int] = train_gen.class_indices
        self.experiment.record_dataset_info({
            "dataset_dir":    str(processed_dir),
            "train_samples":  train_gen.samples,
            "val_samples":    val_gen.samples,
            "class_names":    list(gen_class_map.keys()),
            "class_to_index": gen_class_map,
            "batch_size":     self.cfg.batch_size,
            "class_weights":  self.cfg.class_weights,
        })
        self.experiment.save()

        logger.info(
            f"Generators built | train={train_gen.samples} "
            f"val={val_gen.samples} batch={self.cfg.batch_size}"
        )
        return train_gen, val_gen

    def _build_model(self) -> None:
        """Build and compile the model for Phase 1."""
        self.model = build_model(
            self.cfg.architecture,
            input_shape=(self.cfg.image_size, self.cfg.image_size, 3),
            num_classes=self.cfg.num_classes,
            learning_rate=self.cfg.learning_rate,
        )
        logger.info(
            f"Model built | architecture={self.cfg.architecture} "
            f"params={self.model.count_params():,}"
        )

    def _train_phase1(self, train_gen, val_gen) -> Dict[str, Any]:
        """Phase 1: train only the classification head (backbone frozen)."""
        assert self.model is not None, "Call _build_model() before _train_phase1()"

        logger.info(
            f"Phase 1 start | max_epochs={self.cfg.epochs} "
            f"lr={self.cfg.learning_rate}"
        )

        callbacks_p1 = build_callbacks(
            self.cfg,
            self.experiment_id,
            phase=1,
        )

        history_p1 = self.model.fit(
            train_gen,
            epochs=self.cfg.epochs,
            validation_data=val_gen,
            callbacks=callbacks_p1,
            class_weight=self.cfg.class_weight_map,
            verbose=1,
        )

        hist_dict = {
            k: [float(v) for v in vals]
            for k, vals in history_p1.history.items()
        }
        self.experiment.record_phase_history(1, hist_dict)

        # Save checkpoint info sidecar
        save_checkpoint_info(
            self.cfg,
            self.experiment_id,
            metrics={
                k: float(vals[-1])
                for k, vals in history_p1.history.items()
            },
            epoch=len(history_p1.history.get("loss", [])) - 1,
            phase=1,
        )
        self.experiment.save()

        epochs_p1 = len(history_p1.history.get("loss", []))
        val_acc_p1 = float(history_p1.history.get("val_accuracy", [0.0])[-1])
        logger.info(
            f"Phase 1 complete | epochs={epochs_p1} val_accuracy={val_acc_p1:.4f}"
        )
        return hist_dict

    def _train_phase2(
        self,
        train_gen,
        val_gen,
    ) -> Dict[str, Any]:
        """Phase 2: fine-tune top backbone layers (skipped for CNN or if disabled)."""
        assert self.model is not None

        if not self.cfg.fine_tune or self.cfg.architecture == "cnn":
            logger.info(
                "Phase 2 skipped "
                f"(fine_tune={self.cfg.fine_tune} arch={self.cfg.architecture})"
            )
            return {}

        logger.info(
            f"Phase 2 start | unfreeze={self.cfg.fine_tune_layers} layers "
            f"max_epochs={self.cfg.fine_tune_epochs} "
            f"lr={self.cfg.effective_fine_tune_lr}"
        )

        self.model = unfreeze_top_layers(
            self.model,
            n_layers=self.cfg.fine_tune_layers,
        )
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(
                learning_rate=self.cfg.effective_fine_tune_lr
            ),
            loss="categorical_crossentropy",
            metrics=[
                "accuracy",
                tf.keras.metrics.AUC(name="auc"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
            ],
        )

        callbacks_p2 = build_callbacks(
            self.cfg,
            self.experiment_id,
            phase=2,
        )

        history_p2 = self.model.fit(
            train_gen,
            epochs=self.cfg.fine_tune_epochs,
            validation_data=val_gen,
            callbacks=callbacks_p2,
            class_weight=self.cfg.class_weight_map,
            verbose=1,
        )

        hist_dict = {
            k: [float(v) for v in vals]
            for k, vals in history_p2.history.items()
        }
        self.experiment.record_phase_history(2, hist_dict)

        # Update checkpoint info with Phase-2 metrics
        save_checkpoint_info(
            self.cfg,
            self.experiment_id,
            metrics={
                k: float(vals[-1])
                for k, vals in history_p2.history.items()
            },
            epoch=len(history_p2.history.get("loss", [])) - 1,
            phase=2,
        )
        self.experiment.save()

        epochs_p2 = len(history_p2.history.get("loss", []))
        val_acc_p2 = float(history_p2.history.get("val_accuracy", [0.0])[-1])
        logger.info(
            f"Phase 2 complete | epochs={epochs_p2} val_accuracy={val_acc_p2:.4f}"
        )
        return hist_dict

    def _save_final_model(self) -> Dict[str, Any]:
        """Save the final model (SavedModel + H5) and return path dict."""
        assert self.model is not None

        saved_paths = save_keras_model(
            self.model,
            self.cfg.architecture,
            output_dir=self.cfg.resolved_output_dir,
            metadata={
                "experiment_id":  self.experiment_id,
                "architecture":   self.cfg.architecture,
                "epochs_phase1":  len(
                    self.experiment.phase1_history.get("loss", [])
                ),
                "epochs_phase2":  len(
                    self.experiment.phase2_history.get("loss", [])
                ),
                "best_val_accuracy": self.experiment.best_val_accuracy,
                "final_val_loss":    self.experiment.final_val_loss,
                "learning_rate":     self.cfg.learning_rate,
                "batch_size":        self.cfg.batch_size,
                "fine_tuned":        self.cfg.fine_tune and self.cfg.architecture != "cnn",
            },
        )

        logger.info(f"Final model saved → {saved_paths['model_dir']}")
        return saved_paths

    def _evaluate(self, model_paths: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the saved model against the test split (if it exists)."""
        test_dir = self.cfg.resolved_dataset_dir / "test"

        if not test_dir.exists() or not any(test_dir.iterdir()):
            logger.warning(
                f"No test split found at {test_dir} — skipping evaluation."
            )
            return {}

        try:
            metrics = evaluate_model(
                model_name=self.cfg.architecture,
                dataset_dir=str(test_dir),
                batch_size=self.cfg.batch_size,
            )
            self.experiment.record_eval_metrics(metrics)
            self.experiment.save()
            logger.info(
                f"Evaluation complete | "
                f"accuracy={metrics.get('accuracy', 0):.4f} "
                f"f1={metrics.get('f1', 0):.4f}"
            )
            return metrics
        except Exception as exc:
            logger.warning(f"Post-training evaluation failed (non-fatal): {exc}")
            return {}

    def _build_result_summary(self) -> Dict[str, Any]:
        """Assemble the dict returned from ``run()``."""
        return {
            "experiment_id":       self.experiment_id,
            "architecture":        self.cfg.architecture,
            "epochs_phase1":       len(
                self.experiment.phase1_history.get("loss", [])
            ),
            "epochs_phase2":       len(
                self.experiment.phase2_history.get("loss", [])
            ),
            "best_val_accuracy":   self.experiment.best_val_accuracy,
            "final_val_loss":      self.experiment.final_val_loss,
            "training_duration_s": self.experiment.duration_s,
            "eval_metrics":        self.experiment.eval_metrics,
            "model_paths":         self.experiment.model_paths,
            "phase1_history":      self.experiment.phase1_history,
            "phase2_history":      self.experiment.phase2_history,
            "status":              self.experiment.status,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────────────────────────────────────

def train(
    architecture: str = "efficientnet",
    *,
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    dataset_dir: Optional[str] = None,
    fine_tune: bool = True,
    fine_tune_layers: int = 20,
    fine_tune_epochs: int = 10,
    fine_tune_lr: Optional[float] = None,
    class_weights: Optional[Dict[str, float]] = None,
    seed: int = 42,
    aug_cfg: Optional[AugmentationConfig] = None,
    experiments_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper: build a ``TrainingConfig`` + ``Trainer`` and run.

    Parameters
    ----------
    architecture : str
        One of "cnn" | "vgg16" | "resnet50" | "efficientnet".
    epochs : int
        Maximum Phase-1 epochs.
    batch_size : int
        Mini-batch size.
    learning_rate : float
        Phase-1 Adam learning rate.
    dataset_dir : str | None
        Processed dataset root (``train/`` / ``val/`` / ``test/`` inside).
        Defaults to ``settings.dataset_processed_dir``.
    fine_tune : bool
        Run Phase-2 fine-tuning.
    fine_tune_layers : int
        Backbone layers to unfreeze in Phase 2.
    fine_tune_epochs : int
        Maximum Phase-2 epochs.
    fine_tune_lr : float | None
        Phase-2 learning rate (default: ``learning_rate / 10``).
    class_weights : dict[str, float] | None
        Per-class weight map keyed by class name.
    seed : int
        Random seed.
    aug_cfg : AugmentationConfig | None
        Augmentation config for training generator.
    experiments_dir : Path | None
        Override the experiment storage location.

    Returns
    -------
    dict
        Result summary from ``Trainer.run()``.
    """
    cfg = TrainingConfig(
        architecture=architecture,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        dataset_dir=dataset_dir,
        fine_tune=fine_tune,
        fine_tune_layers=fine_tune_layers,
        fine_tune_epochs=fine_tune_epochs,
        fine_tune_lr=fine_tune_lr,
        class_weights=class_weights,
        seed=seed,
        image_size=settings.image_size,
        num_classes=settings.num_classes,
        class_names=settings.classes,
    )
    trainer = Trainer(cfg, aug_cfg=aug_cfg, experiments_dir=experiments_dir)
    return trainer.run()


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point:  python -m training.trainer
# ─────────────────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m training.trainer",
        description="Train a brain tumour classification model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--architecture", "-a",
        default="efficientnet",
        choices=["cnn", "vgg16", "resnet50", "efficientnet"],
        help="Model architecture to train.",
    )
    p.add_argument(
        "--epochs", "-e",
        type=int,
        default=30,
        help="Maximum Phase-1 epochs.",
    )
    p.add_argument(
        "--batch-size", "-b",
        type=int,
        default=32,
        dest="batch_size",
        help="Mini-batch size.",
    )
    p.add_argument(
        "--learning-rate", "--lr",
        type=float,
        default=1e-4,
        dest="learning_rate",
        help="Phase-1 Adam learning rate.",
    )
    p.add_argument(
        "--dataset-dir",
        default=None,
        dest="dataset_dir",
        help="Processed dataset root directory.",
    )
    p.add_argument(
        "--no-fine-tune",
        action="store_false",
        dest="fine_tune",
        default=True,
        help="Disable Phase-2 fine-tuning.",
    )
    p.add_argument(
        "--fine-tune-layers",
        type=int,
        default=20,
        dest="fine_tune_layers",
        help="Backbone layers to unfreeze in Phase 2.",
    )
    p.add_argument(
        "--fine-tune-epochs",
        type=int,
        default=10,
        dest="fine_tune_epochs",
        help="Maximum Phase-2 epochs.",
    )
    p.add_argument(
        "--fine-tune-lr",
        type=float,
        default=None,
        dest="fine_tune_lr",
        help="Phase-2 learning rate (default: lr/10).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return p


def _main() -> None:
    """CLI entry point."""
    import json as _json

    parser = _build_arg_parser()
    args = parser.parse_args()

    logger.info(
        f"CLI training request | "
        f"arch={args.architecture} epochs={args.epochs} "
        f"batch={args.batch_size} lr={args.learning_rate}"
    )

    result = train(
        architecture=args.architecture,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        dataset_dir=args.dataset_dir,
        fine_tune=args.fine_tune,
        fine_tune_layers=args.fine_tune_layers,
        fine_tune_epochs=args.fine_tune_epochs,
        fine_tune_lr=args.fine_tune_lr,
        seed=args.seed,
    )

    # Pretty-print summary (JSON-serialisable subset)
    summary = {
        k: v for k, v in result.items()
        if k not in ("phase1_history", "phase2_history", "eval_metrics")
    }
    print("\n" + "=" * 60)
    print("Training complete")
    print("=" * 60)
    print(_json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    _main()
