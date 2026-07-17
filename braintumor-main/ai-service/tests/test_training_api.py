"""
tests/test_training_api.py — Integration tests for the training v2 API endpoints.

Endpoints under test
---------------------
POST /api/v1/train/start
GET  /api/v1/train/status/{job_id}
GET  /api/v1/train/experiments
GET  /api/v1/train/experiments/{experiment_id}

All tests use the FastAPI TestClient and mock out the actual
Trainer.run() call so no real training or GPU is needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.training.job_store import get_job_store


@pytest.fixture(autouse=True)
def _reset_job_store():
    """Clear in-process job store between tests to avoid state leakage."""
    store = get_job_store()
    store._store.clear()
    yield
    store._store.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/train/start
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainStart:
    def _mock_trainer(self):
        """Return a mock Trainer that does nothing when run() is called."""
        trainer = MagicMock()
        trainer.experiment_id = "cnn-20240715-000000-aabbccdd"
        trainer.run = MagicMock(return_value={"status": "completed"})
        return trainer

    def test_returns_202(self, client):
        # Trainer is imported inside the route function body:
        # "from training.trainer import Trainer"
        # so we must patch it at that import location.
        with patch("training.trainer.Trainer") as MockTrainer:
            MockTrainer.return_value = self._mock_trainer()
            resp = client.post(
                "/api/v1/train/start",
                json={"architecture": "cnn", "epochs": 1, "batch_size": 4},
            )
        assert resp.status_code == 202

    def test_response_has_job_id(self, client):
        with patch("training.trainer.Trainer") as MockTrainer:
            MockTrainer.return_value = self._mock_trainer()
            resp = client.post(
                "/api/v1/train/start",
                json={"architecture": "cnn", "epochs": 1},
            )
        data = resp.json()
        assert data["success"] is True
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    def test_response_has_experiment_id(self, client):
        trainer = self._mock_trainer()
        with patch("training.trainer.Trainer") as MockTrainer:
            MockTrainer.return_value = trainer
            resp = client.post(
                "/api/v1/train/start",
                json={"architecture": "cnn", "epochs": 1},
            )
        data = resp.json()
        assert data["experiment_id"] == trainer.experiment_id

    def test_invalid_architecture_returns_422(self, client):
        resp = client.post(
            "/api/v1/train/start",
            json={"architecture": "densenet", "epochs": 1},
        )
        assert resp.status_code == 422

    def test_job_stored_in_job_store(self, client):
        with patch("training.trainer.Trainer") as MockTrainer:
            MockTrainer.return_value = self._mock_trainer()
            resp = client.post(
                "/api/v1/train/start",
                json={"architecture": "cnn", "epochs": 1},
            )
        job_id = resp.json()["job_id"]
        store = get_job_store()
        job = store.get(job_id)
        assert job is not None
        assert job["status"] in ("running", "queued", "completed")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/train/status/{job_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainStatus:
    def _create_job(self) -> str:
        store  = get_job_store()
        job_id = store.create_job({"architecture": "cnn"})
        store.mark_running(job_id, experiment_id="cnn-20240715-aabb")
        return job_id

    def test_existing_job_returns_200(self, client):
        job_id = self._create_job()
        resp   = client.get(f"/api/v1/train/status/{job_id}")
        assert resp.status_code == 200

    def test_response_contains_job_data(self, client):
        job_id = self._create_job()
        resp   = client.get(f"/api/v1/train/status/{job_id}")
        data   = resp.json()
        assert data["success"] is True
        assert data["data"]["job_id"] == job_id

    def test_status_field_is_present(self, client):
        job_id = self._create_job()
        resp   = client.get(f"/api/v1/train/status/{job_id}")
        assert "status" in resp.json()["data"]

    def test_unknown_job_id_returns_404(self, client):
        resp = client.get("/api/v1/train/status/00000000does-not-exist")
        assert resp.status_code == 404

    def test_completed_job_has_result(self, client):
        store  = get_job_store()
        job_id = store.create_job({"architecture": "cnn"})
        store.mark_running(job_id, experiment_id="cnn-exp-001")
        store.mark_completed(job_id, result={"accuracy": 0.9})

        resp = client.get(f"/api/v1/train/status/{job_id}")
        data = resp.json()["data"]
        assert data["status"]             == "completed"
        assert data["result"]["accuracy"] == pytest.approx(0.9)

    def test_failed_job_has_error(self, client):
        store  = get_job_store()
        job_id = store.create_job({"architecture": "cnn"})
        store.mark_running(job_id, experiment_id="cnn-exp-002")
        store.mark_failed(job_id, error="Dataset not found")

        resp = client.get(f"/api/v1/train/status/{job_id}")
        data = resp.json()["data"]
        assert data["status"] == "failed"
        assert "Dataset not found" in data["error"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/train/experiments
# ─────────────────────────────────────────────────────────────────────────────

class TestListExperiments:
    def _populate_registry(self, tmp_path: Path, n: int = 3):
        """Create n completed experiment records in a temp dir."""
        from training.config import TrainingConfig
        from training.experiment import Experiment

        cfg = TrainingConfig(architecture="cnn", epochs=1)
        for _ in range(n):
            exp = Experiment.create(cfg, experiments_dir=tmp_path)
            exp.update_status("completed")
            exp.save()

    def test_returns_200(self, client, tmp_path):
        self._populate_registry(tmp_path)
        from training.experiment import ExperimentRegistry
        fake_reg = ExperimentRegistry(tmp_path)
        with patch("training.experiment.ExperimentRegistry", return_value=fake_reg):
            resp = client.get("/api/v1/train/experiments")
        assert resp.status_code == 200

    def test_response_has_data_and_total(self, client, tmp_path):
        self._populate_registry(tmp_path, n=3)
        from training.experiment import ExperimentRegistry
        fake_reg = ExperimentRegistry(tmp_path)
        with patch("training.experiment.ExperimentRegistry", return_value=fake_reg):
            resp = client.get("/api/v1/train/experiments")
        body = resp.json()
        assert "data"  in body
        assert "total" in body
        assert isinstance(body["data"], list)

    def test_limit_query_param(self, client, tmp_path):
        self._populate_registry(tmp_path, n=5)
        from training.experiment import ExperimentRegistry
        fake_reg = ExperimentRegistry(tmp_path)
        with patch("training.experiment.ExperimentRegistry", return_value=fake_reg):
            resp = client.get("/api/v1/train/experiments?limit=2")
        body = resp.json()
        assert len(body["data"]) <= 2

    def test_returns_200_with_real_default_registry(self, client):
        """No patch — just confirm endpoint doesn't crash with empty registry."""
        resp = client.get("/api/v1/train/experiments")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/train/experiments/{experiment_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestGetExperiment:
    def _make_experiment(self, tmp_path: Path):
        from training.config import TrainingConfig
        from training.experiment import Experiment
        cfg = TrainingConfig(architecture="cnn", epochs=1)
        exp = Experiment.create(cfg, experiments_dir=tmp_path)
        exp.record_eval_metrics({"accuracy": 0.95})
        exp.save()
        return exp

    def test_existing_experiment_returns_200(self, client, tmp_path):
        exp      = self._make_experiment(tmp_path)
        from training.experiment import ExperimentRegistry
        fake_reg = ExperimentRegistry(tmp_path)
        with patch("training.experiment.ExperimentRegistry", return_value=fake_reg):
            resp = client.get(f"/api/v1/train/experiments/{exp.experiment_id}")
        assert resp.status_code == 200

    def test_response_contains_experiment_data(self, client, tmp_path):
        exp      = self._make_experiment(tmp_path)
        from training.experiment import ExperimentRegistry
        fake_reg = ExperimentRegistry(tmp_path)
        with patch("training.experiment.ExperimentRegistry", return_value=fake_reg):
            resp = client.get(f"/api/v1/train/experiments/{exp.experiment_id}")
        data = resp.json()["data"]
        assert data["experiment_id"] == exp.experiment_id
        assert data["eval_metrics"]["accuracy"] == pytest.approx(0.95)

    def test_missing_experiment_returns_404(self, client, tmp_path):
        from training.experiment import ExperimentRegistry
        fake_reg = ExperimentRegistry(tmp_path)
        with patch("training.experiment.ExperimentRegistry", return_value=fake_reg):
            resp = client.get("/api/v1/train/experiments/nonexistent-id")
        assert resp.status_code == 404

    def test_missing_experiment_returns_404_default_registry(self, client):
        """No patch — just confirm 404 with a clearly fake ID."""
        resp = client.get("/api/v1/train/experiments/this-id-does-not-exist-xyz")
        assert resp.status_code == 404
