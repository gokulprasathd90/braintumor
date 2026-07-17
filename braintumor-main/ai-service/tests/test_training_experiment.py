"""
tests/test_training_experiment.py — Unit tests for training.experiment.

Tests
-----
- Experiment.create() produces a well-formed record.
- Experiment.save() writes experiment.json and training_config.json.
- Experiment.load() round-trips through JSON correctly.
- Status transitions (update_status) work and reject invalid values.
- Mutation helpers (record_phase_history, record_eval_metrics, ...) work.
- Computed properties: best_val_accuracy, final_val_loss, epochs_trained.
- ExperimentRegistry.upsert() inserts and updates entries.
- ExperimentRegistry.list_experiments() filters by architecture and status.
- ExperimentRegistry.get() returns the full experiment dict.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from training.config import TrainingConfig
from training.experiment import Experiment, ExperimentRegistry, EXPERIMENT_STATUSES


def _make_cfg() -> TrainingConfig:
    return TrainingConfig(architecture="cnn", epochs=5, batch_size=4)


def _make_exp(tmp_path: Path) -> Experiment:
    return Experiment.create(_make_cfg(), experiments_dir=tmp_path)


# ─────────────────────────────────────────────────────────────────────────────
# Creation
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentCreate:
    def test_returns_experiment_instance(self, tmp_path):
        exp = _make_exp(tmp_path)
        assert isinstance(exp, Experiment)

    def test_experiment_id_contains_architecture(self, tmp_path):
        exp = _make_exp(tmp_path)
        assert "cnn" in exp.experiment_id

    def test_status_is_created(self, tmp_path):
        assert _make_exp(tmp_path).status == "created"

    def test_config_snapshot_stored(self, tmp_path):
        exp = _make_exp(tmp_path)
        assert exp.config["architecture"] == "cnn"
        assert exp.config["epochs"] == 5

    def test_created_at_set(self, tmp_path):
        exp = _make_exp(tmp_path)
        assert exp.created_at is not None
        assert "T" in exp.created_at  # ISO-8601 format


# ─────────────────────────────────────────────────────────────────────────────
# Persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentPersistence:
    def test_save_creates_experiment_json(self, tmp_path):
        exp = _make_exp(tmp_path)
        path = exp.save()
        assert path.exists()
        assert path.name == "experiment.json"

    def test_save_creates_training_config_json(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.save()
        cfg_path = exp.experiment_dir / "training_config.json"
        assert cfg_path.exists()

    def test_save_content_is_valid_json(self, tmp_path):
        exp = _make_exp(tmp_path)
        path = exp.save()
        with open(path) as fh:
            data = json.load(fh)
        assert data["experiment_id"] == exp.experiment_id

    def test_load_round_trip(self, tmp_path):
        exp1 = _make_exp(tmp_path)
        exp1.update_status("running")
        exp1.save()

        exp2 = Experiment.load(exp1.experiment_id, tmp_path)
        assert exp2.experiment_id == exp1.experiment_id
        assert exp2.status        == "running"
        assert exp2.architecture  == exp1.architecture

    def test_load_raises_for_missing_experiment(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Experiment.load("nonexistent-id-xyz", tmp_path)


# ─────────────────────────────────────────────────────────────────────────────
# Status transitions
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentStatus:
    @pytest.mark.parametrize("s", EXPERIMENT_STATUSES)
    def test_valid_status_accepted(self, tmp_path, s):
        exp = _make_exp(tmp_path)
        exp.update_status(s)
        assert exp.status == s

    def test_invalid_status_raises(self, tmp_path):
        exp = _make_exp(tmp_path)
        with pytest.raises(ValueError):
            exp.update_status("training")   # not a valid status

    def test_running_sets_started_at(self, tmp_path):
        exp = _make_exp(tmp_path)
        assert exp.started_at is None
        exp.update_status("running")
        assert exp.started_at is not None

    def test_completed_sets_finished_at(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.update_status("completed")
        assert exp.finished_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# Mutation helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentMutations:
    def test_record_phase1_history(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_phase_history(1, {"loss": [0.5, 0.4], "val_accuracy": [0.7, 0.8]})
        assert exp.phase1_history["loss"] == pytest.approx([0.5, 0.4])

    def test_record_phase2_history(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_phase_history(2, {"loss": [0.3], "val_accuracy": [0.9]})
        assert exp.phase2_history["val_accuracy"] == pytest.approx([0.9])

    def test_record_eval_metrics(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_eval_metrics({"accuracy": 0.95, "f1": 0.94})
        assert exp.eval_metrics["accuracy"] == pytest.approx(0.95)

    def test_record_dataset_info(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_dataset_info({"train_samples": 100, "val_samples": 20})
        assert exp.dataset_info["train_samples"] == 100

    def test_record_error_sets_status_failed(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_error(ValueError("something went wrong"))
        assert exp.status == "failed"
        assert "ValueError" in exp.error

    def test_set_duration(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.set_duration(123.456)
        assert exp.duration_s == pytest.approx(123.46)


# ─────────────────────────────────────────────────────────────────────────────
# Computed properties
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentProperties:
    def test_best_val_accuracy_none_when_no_history(self, tmp_path):
        assert _make_exp(tmp_path).best_val_accuracy is None

    def test_best_val_accuracy_from_phase1(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_phase_history(1, {"val_accuracy": [0.7, 0.85, 0.82]})
        assert exp.best_val_accuracy == pytest.approx(0.85)

    def test_best_val_accuracy_max_across_phases(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_phase_history(1, {"val_accuracy": [0.8, 0.85]})
        exp.record_phase_history(2, {"val_accuracy": [0.87, 0.92]})
        assert exp.best_val_accuracy == pytest.approx(0.92)

    def test_final_val_loss_from_phase2_when_present(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_phase_history(1, {"val_loss": [0.5, 0.4]})
        exp.record_phase_history(2, {"val_loss": [0.3, 0.25]})
        assert exp.final_val_loss == pytest.approx(0.25)

    def test_epochs_trained_sum_both_phases(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_phase_history(1, {"loss": [0.5, 0.4, 0.35]})
        exp.record_phase_history(2, {"loss": [0.3, 0.28]})
        assert exp.epochs_trained == 5

    def test_to_summary_contains_required_keys(self, tmp_path):
        exp     = _make_exp(tmp_path)
        summary = exp.to_summary()
        for key in ("experiment_id", "architecture", "status", "created_at"):
            assert key in summary


# ─────────────────────────────────────────────────────────────────────────────
# ExperimentRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentRegistry:
    def test_upsert_adds_new_entry(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.save()

        registry = ExperimentRegistry(tmp_path)
        entries  = registry.list_experiments()
        ids      = [e["experiment_id"] for e in entries]
        assert exp.experiment_id in ids

    def test_upsert_updates_existing_entry(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.save()

        exp.update_status("completed")
        exp.save()

        registry = ExperimentRegistry(tmp_path)
        entries  = registry.list_experiments()
        entry    = next(
            e for e in entries
            if e["experiment_id"] == exp.experiment_id
        )
        assert entry["status"] == "completed"

    def test_list_experiments_filter_by_architecture(self, tmp_path):
        cfg_cnn = TrainingConfig(architecture="cnn", epochs=2)
        cfg_vgg = TrainingConfig(architecture="vgg16", epochs=2)

        exp_cnn = Experiment.create(cfg_cnn, experiments_dir=tmp_path)
        exp_vgg = Experiment.create(cfg_vgg, experiments_dir=tmp_path)
        exp_cnn.save()
        exp_vgg.save()

        registry = ExperimentRegistry(tmp_path)
        cnn_only = registry.list_experiments(architecture="cnn")
        assert all(e["architecture"] == "cnn" for e in cnn_only)

    def test_list_experiments_filter_by_status(self, tmp_path):
        exp1 = _make_exp(tmp_path)
        exp2 = _make_exp(tmp_path)
        exp1.update_status("completed")
        exp1.save()
        exp2.update_status("failed")
        exp2.save()

        registry   = ExperimentRegistry(tmp_path)
        completed  = registry.list_experiments(status="completed")
        assert all(e["status"] == "completed" for e in completed)

    def test_get_returns_full_dict(self, tmp_path):
        exp = _make_exp(tmp_path)
        exp.record_eval_metrics({"accuracy": 0.9})
        exp.save()

        registry = ExperimentRegistry(tmp_path)
        data     = registry.get(exp.experiment_id)
        assert data is not None
        assert "eval_metrics" in data
        assert data["eval_metrics"]["accuracy"] == pytest.approx(0.9)

    def test_get_returns_none_for_missing(self, tmp_path):
        registry = ExperimentRegistry(tmp_path)
        assert registry.get("does-not-exist") is None

    def test_list_experiments_respects_limit(self, tmp_path):
        registry = ExperimentRegistry(tmp_path)
        for _ in range(5):
            exp = _make_exp(tmp_path)
            exp.save()
        assert len(registry.list_experiments(limit=3)) == 3
