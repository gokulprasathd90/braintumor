"""
tests/test_metrics.py — Tests for the metrics & monitoring package.

Coverage
--------
TestSystemMetrics       system.py  — snapshot structure, types, defaults
TestInferenceStore      inference.py — record(), record_batch(), to_dict()
TestInferenceHelpers    inference.py — module-level helpers
TestTrainingMetrics     training.py — aggregation, duration helpers
TestMetricsStorage      storage.py  — save/load, in-memory buffer, disk cold path
TestDashboardOverview   dashboard.py — composite overview, alerts
TestDashboardHistory    dashboard.py — get_history_summary
TestDashboardAPIRoutes  routes.py   — GET /dashboard/*
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# system.py
# ─────────────────────────────────────────────────────────────────────────────

class TestSystemMetrics:

    def test_returns_dict(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert isinstance(result, dict)

    def test_timestamp_present_and_string(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]

    def test_uptime_seconds_positive(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0

    def test_cpu_percent_in_range_or_none(self) -> None:
        from app.metrics.system import get_system_metrics
        cpu = get_system_metrics().get("cpu_percent")
        if cpu is not None:
            assert 0.0 <= cpu <= 100.0

    def test_ram_percent_in_range_or_none(self) -> None:
        from app.metrics.system import get_system_metrics
        ram = get_system_metrics().get("ram_percent")
        if ram is not None:
            assert 0.0 <= ram <= 100.0

    def test_disk_percent_in_range_or_none(self) -> None:
        from app.metrics.system import get_system_metrics
        disk = get_system_metrics().get("disk_percent")
        if disk is not None:
            assert 0.0 <= disk <= 100.0

    def test_gpu_available_is_bool(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert isinstance(result["gpu_available"], bool)

    def test_gpus_is_list(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert isinstance(result["gpus"], list)

    def test_platform_present(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert isinstance(result.get("platform"), str)
        assert len(result["platform"]) > 0

    def test_python_version_present(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        assert isinstance(result.get("python_version"), str)

    def test_process_pid_is_int(self) -> None:
        from app.metrics.system import get_system_metrics
        pid = get_system_metrics().get("process_pid")
        if pid is not None:
            assert isinstance(pid, int)
            assert pid > 0

    def test_process_ram_mb_non_negative(self) -> None:
        from app.metrics.system import get_system_metrics
        ram = get_system_metrics().get("process_ram_mb")
        if ram is not None:
            assert ram >= 0

    def test_cpu_per_core_is_list(self) -> None:
        from app.metrics.system import get_system_metrics
        cores = get_system_metrics().get("cpu_per_core")
        assert isinstance(cores, list)

    def test_ram_total_mb_positive_or_none(self) -> None:
        from app.metrics.system import get_system_metrics
        val = get_system_metrics().get("ram_total_mb")
        if val is not None:
            assert val > 0

    def test_disk_total_gb_positive_or_none(self) -> None:
        from app.metrics.system import get_system_metrics
        val = get_system_metrics().get("disk_total_gb")
        if val is not None:
            assert val > 0

    def test_all_required_keys_present(self) -> None:
        from app.metrics.system import get_system_metrics
        result = get_system_metrics()
        required = {
            "timestamp", "uptime_seconds", "platform", "python_version",
            "cpu_percent", "cpu_per_core", "ram_percent", "disk_percent",
            "gpu_available", "gpus", "process_pid", "process_ram_mb",
        }
        for key in required:
            assert key in result, f"Missing key: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# inference.py — InferenceMetricsStore
# ─────────────────────────────────────────────────────────────────────────────

class TestInferenceStore:

    def _fresh_store(self):
        from app.metrics.inference import InferenceMetricsStore
        return InferenceMetricsStore()

    def test_initial_total_is_zero(self) -> None:
        store = self._fresh_store()
        assert store.to_dict()["total_predictions"] == 0

    def test_record_increments_total(self) -> None:
        store = self._fresh_store()
        store.record(
            model_name="efficientnet",
            predicted_class="glioma",
            confidence=0.92,
            timing_ms=38.5,
            success=True,
        )
        assert store.to_dict()["total_predictions"] == 1

    def test_record_success_increments_succeeded(self) -> None:
        store = self._fresh_store()
        store.record(
            model_name="efficientnet", predicted_class="glioma",
            confidence=0.9, timing_ms=40.0, success=True,
        )
        assert store.to_dict()["succeeded"] == 1
        assert store.to_dict()["failed"] == 0

    def test_record_failure_increments_failed(self) -> None:
        store = self._fresh_store()
        store.record(
            model_name="cnn", predicted_class="unknown",
            confidence=0.0, timing_ms=5.0, success=False,
        )
        assert store.to_dict()["failed"] == 1
        assert store.to_dict()["succeeded"] == 0

    def test_success_rate_all_success(self) -> None:
        store = self._fresh_store()
        for _ in range(4):
            store.record(
                model_name="efficientnet", predicted_class="glioma",
                confidence=0.9, timing_ms=40.0, success=True,
            )
        assert store.to_dict()["success_rate"] == pytest.approx(1.0)

    def test_success_rate_mixed(self) -> None:
        store = self._fresh_store()
        for i in range(3):
            store.record(
                model_name="efficientnet", predicted_class="glioma",
                confidence=0.9, timing_ms=40.0, success=(i < 2),
            )
        assert store.to_dict()["success_rate"] == pytest.approx(2 / 3, abs=1e-4)

    def test_timing_avg_computed(self) -> None:
        store = self._fresh_store()
        for ms in [10.0, 20.0, 30.0]:
            store.record(
                model_name="efficientnet", predicted_class="glioma",
                confidence=0.9, timing_ms=ms, success=True,
            )
        assert store.to_dict()["avg_latency_ms"] == pytest.approx(20.0)

    def test_per_model_counts_tracked(self) -> None:
        store = self._fresh_store()
        store.record(model_name="cnn", predicted_class="glioma", confidence=0.8, timing_ms=50.0, success=True)
        store.record(model_name="efficientnet", predicted_class="glioma", confidence=0.9, timing_ms=40.0, success=True)
        store.record(model_name="efficientnet", predicted_class="notumor", confidence=0.95, timing_ms=35.0, success=True)
        counts = store.to_dict()["per_model_counts"]
        assert counts["cnn"] == 1
        assert counts["efficientnet"] == 2

    def test_class_counts_tracked(self) -> None:
        store = self._fresh_store()
        for cls in ["glioma", "glioma", "notumor"]:
            store.record(
                model_name="efficientnet", predicted_class=cls,
                confidence=0.9, timing_ms=40.0, success=True,
            )
        dist = store.to_dict()["class_distribution"]
        assert dist["glioma"] == 2
        assert dist["notumor"] == 1

    def test_confidence_histogram_bucket_assigned(self) -> None:
        store = self._fresh_store()
        store.record(
            model_name="efficientnet", predicted_class="glioma",
            confidence=0.97, timing_ms=40.0, success=True,
        )
        hist = store.to_dict()["confidence_distribution"]
        assert sum(hist["counts"]) == 1

    def test_recent_predictions_capped_at_100(self) -> None:
        store = self._fresh_store()
        for i in range(120):
            store.record(
                model_name="efficientnet", predicted_class="glioma",
                confidence=0.9, timing_ms=40.0, success=True,
            )
        recent = store.to_dict()["recent_predictions"]
        assert len(recent) <= 100

    def test_record_batch_increments_batch_total(self) -> None:
        store = self._fresh_store()
        store.record_batch(
            model_name="efficientnet", total=5,
            succeeded=4, failed=1, timing_ms=200.0,
            class_distribution={"glioma": 3, "notumor": 1},
        )
        d = store.to_dict()
        assert d["batch_runs"] == 1
        assert d["batch_images_processed"] == 5

    def test_record_batch_merges_class_distribution(self) -> None:
        store = self._fresh_store()
        store.record_batch(
            model_name="efficientnet", total=3, succeeded=3, failed=0,
            timing_ms=100.0, class_distribution={"glioma": 2, "notumor": 1},
        )
        store.record_batch(
            model_name="efficientnet", total=2, succeeded=2, failed=0,
            timing_ms=80.0, class_distribution={"glioma": 1, "meningioma": 1},
        )
        dist = store.to_dict()["class_distribution"]
        assert dist["glioma"] == 3
        assert dist["notumor"] == 1
        assert dist["meningioma"] == 1

    def test_reset_clears_all_counts(self) -> None:
        store = self._fresh_store()
        store.record(
            model_name="cnn", predicted_class="glioma",
            confidence=0.8, timing_ms=50.0, success=True,
        )
        store.reset()
        d = store.to_dict()
        assert d["total_predictions"] == 0
        assert d["succeeded"] == 0
        assert d["batch_runs"] == 0

    def test_top_classes_sorted_descending(self) -> None:
        store = self._fresh_store()
        for cls, n in [("glioma", 5), ("notumor", 2), ("meningioma", 8)]:
            for _ in range(n):
                store.record(
                    model_name="efficientnet", predicted_class=cls,
                    confidence=0.9, timing_ms=40.0, success=True,
                )
        top = store.to_dict()["top_classes"]
        counts = [t["count"] for t in top]
        assert counts == sorted(counts, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# inference.py — module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestInferenceHelpers:

    def test_get_inference_metrics_returns_dict(self) -> None:
        from app.metrics.inference import get_inference_metrics
        result = get_inference_metrics()
        assert isinstance(result, dict)
        assert "total_predictions" in result

    def test_get_inference_store_returns_singleton(self) -> None:
        from app.metrics.inference import get_inference_store
        a = get_inference_store()
        b = get_inference_store()
        assert a is b

    def test_record_prediction_dict_does_not_raise(self) -> None:
        from app.metrics.inference import record_prediction
        record_prediction({
            "metadata": {"model_name": "efficientnet"},
            "predicted_class": "glioma",
            "confidence": 0.9,
            "timing_ms": 40.0,
            "error": None,
        })

    def test_record_prediction_bad_input_does_not_raise(self) -> None:
        from app.metrics.inference import record_prediction
        record_prediction(None)   # should silently pass
        record_prediction("oops")

    def test_record_batch_prediction_dict_does_not_raise(self) -> None:
        from app.metrics.inference import record_batch_prediction
        record_batch_prediction({
            "model_name": "efficientnet",
            "total": 3, "succeeded": 3, "failed": 0,
            "timing_ms": 120.0,
            "class_distribution": {"glioma": 3},
        })

    def test_confidence_distribution_has_correct_buckets(self) -> None:
        from app.metrics.inference import get_inference_metrics
        dist = get_inference_metrics()["confidence_distribution"]
        assert len(dist["buckets"]) == len(dist["counts"])
        assert len(dist["buckets"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# training.py
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingMetrics:

    def test_returns_dict(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        assert isinstance(result, dict)

    def test_timestamp_present(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        assert "timestamp" in result

    def test_job_counts_are_ints(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        for key in ("total_jobs", "running_jobs", "completed_jobs", "failed_jobs"):
            assert isinstance(result[key], int), f"{key} must be int"
            assert result[key] >= 0

    def test_recent_jobs_is_list(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        assert isinstance(result["recent_jobs"], list)

    def test_recent_experiments_is_list(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        assert isinstance(result["recent_experiments"], list)

    def test_architecture_counts_is_dict(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        assert isinstance(result["architecture_counts"], dict)

    def test_best_val_accuracy_none_or_float(self) -> None:
        from app.metrics.training import get_training_metrics
        val = get_training_metrics().get("best_val_accuracy")
        if val is not None:
            assert 0.0 <= val <= 1.0

    def test_duration_helper_both_none(self) -> None:
        from app.metrics.training import _duration_seconds
        assert _duration_seconds(None, None) is None

    def test_duration_helper_no_end(self) -> None:
        from app.metrics.training import _duration_seconds
        result = _duration_seconds("2024-01-01T00:00:00+00:00", None)
        assert result is None or result >= 0

    def test_duration_helper_both_provided(self) -> None:
        from app.metrics.training import _duration_seconds
        result = _duration_seconds(
            "2024-01-01T00:00:00+00:00",
            "2024-01-01T01:00:00+00:00",
        )
        assert result == pytest.approx(3600.0)

    def test_total_jobs_equals_sum_of_statuses(self) -> None:
        from app.metrics.training import get_training_metrics
        d = get_training_metrics()
        status_sum = d["running_jobs"] + d["completed_jobs"] + d["failed_jobs"] + d["queued_jobs"]
        assert d["total_jobs"] == status_sum

    def test_required_keys_present(self) -> None:
        from app.metrics.training import get_training_metrics
        result = get_training_metrics()
        for key in (
            "timestamp", "total_jobs", "running_jobs", "completed_jobs",
            "failed_jobs", "recent_jobs", "recent_experiments",
            "architecture_counts", "total_experiments",
        ):
            assert key in result, f"Missing key: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# storage.py
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricsStorage:

    def _make_store(self, tmp_path: Path):
        from app.metrics.storage import MetricsStorage
        return MetricsStorage(base_dir=tmp_path)

    def test_save_snapshot_does_not_raise(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        store.save_snapshot({"type": "system", "cpu_percent": 42.0})

    def test_save_adds_timestamp_if_missing(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        snap = {"type": "system", "cpu_percent": 55.0}
        store.save_snapshot(snap)
        history = store.load_history("system", hours=1)
        assert len(history) == 1
        assert "timestamp" in history[0]

    def test_load_history_from_memory_buffer(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        for i in range(5):
            store.save_snapshot({"type": "system", "cpu_percent": float(i)})
        history = store.load_history("system", hours=1)
        assert len(history) == 5

    def test_load_history_respects_max_points(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        for i in range(50):
            store.save_snapshot({"type": "system", "cpu_percent": float(i)})
        history = store.load_history("system", hours=24, max_points=10)
        assert len(history) <= 10

    def test_load_history_empty_store_returns_empty(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        history = store.load_history("system", hours=24)
        assert history == []

    def test_multiple_metric_types_isolated(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        store.save_snapshot({"type": "system", "cpu_percent": 30.0})
        store.save_snapshot({"type": "inference", "total_predictions": 10})
        assert len(store.load_history("system")) == 1
        assert len(store.load_history("inference")) == 1

    def test_load_daily_summary_returns_dict(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        store.save_snapshot({"type": "system", "cpu_percent": 42.0})
        summary = store.load_daily_summary()
        assert isinstance(summary, dict)
        assert "date" in summary

    def test_get_available_dates_empty(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        dates = store.get_available_dates("system")
        assert isinstance(dates, list)
        assert len(dates) == 0

    def test_get_available_dates_after_save(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        store.save_snapshot({"type": "system", "cpu_percent": 50.0})
        dates = store.get_available_dates("system")
        assert len(dates) == 1

    def test_purge_old_files_removes_old(self, tmp_path: Path) -> None:
        # Create a fake "old" jsonl file
        old_file = tmp_path / "system_2020-01-01.jsonl"
        old_file.write_text('{"timestamp":"2020-01-01T00:00:00+00:00","type":"system"}\n')
        store = self._make_store(tmp_path)
        removed = store.purge_old_files(keep_days=30)
        assert removed >= 1
        assert not old_file.exists()

    def test_purge_old_files_keeps_recent(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        store.save_snapshot({"type": "system", "cpu_percent": 20.0})
        removed = store.purge_old_files(keep_days=30)
        assert removed == 0

    def test_get_metrics_store_returns_singleton(self) -> None:
        from app.metrics.storage import get_metrics_store
        a = get_metrics_store()
        b = get_metrics_store()
        assert a is b

    def test_disk_persistence(self, tmp_path: Path) -> None:
        """Snapshots saved to disk should survive a new store instance (cold load)."""
        store1 = self._make_store(tmp_path)
        store1.save_snapshot({"type": "system", "cpu_percent": 77.0})
        # New instance — cold path reads from disk
        store2 = self._make_store(tmp_path)
        history = store2.load_history("system", hours=24)
        assert any(s.get("cpu_percent") == 77.0 for s in history)


# ─────────────────────────────────────────────────────────────────────────────
# dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboardOverview:

    def test_returns_dict(self) -> None:
        from app.metrics.dashboard import get_dashboard_overview
        result = get_dashboard_overview()
        assert isinstance(result, dict)

    def test_required_top_level_keys(self) -> None:
        from app.metrics.dashboard import get_dashboard_overview
        result = get_dashboard_overview()
        for key in ("timestamp", "system", "inference", "training", "models", "alerts"):
            assert key in result, f"Missing key: {key}"

    def test_system_sub_keys(self) -> None:
        from app.metrics.dashboard import get_dashboard_overview
        sys_data = get_dashboard_overview()["system"]
        for key in ("cpu_percent", "ram_percent", "disk_percent", "gpu_available", "uptime_seconds"):
            assert key in sys_data, f"Missing system key: {key}"

    def test_inference_sub_keys(self) -> None:
        from app.metrics.dashboard import get_dashboard_overview
        inf_data = get_dashboard_overview()["inference"]
        for key in ("total_predictions", "succeeded", "failed", "success_rate", "batch_runs"):
            assert key in inf_data, f"Missing inference key: {key}"

    def test_training_sub_keys(self) -> None:
        from app.metrics.dashboard import get_dashboard_overview
        trn_data = get_dashboard_overview()["training"]
        for key in ("total_jobs", "running_jobs", "completed_jobs", "failed_jobs"):
            assert key in trn_data, f"Missing training key: {key}"

    def test_alerts_is_list(self) -> None:
        from app.metrics.dashboard import get_dashboard_overview
        alerts = get_dashboard_overview()["alerts"]
        assert isinstance(alerts, list)

    def test_no_alerts_under_normal_conditions(self) -> None:
        from app.metrics.dashboard import _compute_alerts
        sys_m = {"cpu_percent": 30.0, "ram_percent": 50.0, "disk_percent": 40.0}
        inf_m = {"success_rate": 1.0, "total_predictions": 100, "avg_latency_ms": 50.0}
        alerts = _compute_alerts(sys_m, inf_m)
        assert alerts == []

    def test_cpu_warning_triggered(self) -> None:
        from app.metrics.dashboard import _compute_alerts
        sys_m = {"cpu_percent": 82.0, "ram_percent": 50.0, "disk_percent": 40.0}
        inf_m = {"success_rate": 1.0, "total_predictions": 0, "avg_latency_ms": 50.0}
        alerts = _compute_alerts(sys_m, inf_m)
        assert any(a["domain"] == "system" and a["level"] == "warning" for a in alerts)

    def test_cpu_critical_triggered(self) -> None:
        from app.metrics.dashboard import _compute_alerts
        sys_m = {"cpu_percent": 97.0, "ram_percent": 50.0, "disk_percent": 40.0}
        inf_m = {"success_rate": 1.0, "total_predictions": 0, "avg_latency_ms": 50.0}
        alerts = _compute_alerts(sys_m, inf_m)
        assert any(a["level"] == "critical" for a in alerts)

    def test_low_success_rate_triggers_alert(self) -> None:
        from app.metrics.dashboard import _compute_alerts
        sys_m = {"cpu_percent": 30.0, "ram_percent": 50.0, "disk_percent": 40.0}
        inf_m = {"success_rate": 0.5, "total_predictions": 20, "avg_latency_ms": 50.0}
        alerts = _compute_alerts(sys_m, inf_m)
        assert any(a["domain"] == "inference" for a in alerts)

    def test_alert_has_level_domain_message(self) -> None:
        from app.metrics.dashboard import _compute_alerts
        sys_m = {"cpu_percent": 96.0, "ram_percent": 50.0, "disk_percent": 40.0}
        inf_m = {"success_rate": 1.0, "total_predictions": 0, "avg_latency_ms": 50.0}
        alerts = _compute_alerts(sys_m, inf_m)
        for alert in alerts:
            assert "level" in alert
            assert "domain" in alert
            assert "message" in alert

    def test_high_latency_alert(self) -> None:
        from app.metrics.dashboard import _compute_alerts
        sys_m = {"cpu_percent": 30.0, "ram_percent": 50.0, "disk_percent": 40.0}
        inf_m = {"success_rate": 1.0, "total_predictions": 0, "avg_latency_ms": 3000.0}
        alerts = _compute_alerts(sys_m, inf_m)
        assert any(a["domain"] == "inference" for a in alerts)


class TestDashboardHistory:

    def test_returns_dict_with_required_keys(self) -> None:
        from app.metrics.dashboard import get_history_summary
        result = get_history_summary(metric_type="system", hours=1)
        assert isinstance(result, dict)
        for key in ("metric_type", "hours", "count", "data"):
            assert key in result

    def test_metric_type_preserved(self) -> None:
        from app.metrics.dashboard import get_history_summary
        result = get_history_summary(metric_type="inference", hours=6)
        assert result["metric_type"] == "inference"

    def test_hours_capped_at_168(self) -> None:
        from app.metrics.dashboard import get_history_summary
        result = get_history_summary(metric_type="system", hours=999)
        assert result["hours"] == 168

    def test_data_is_list(self) -> None:
        from app.metrics.dashboard import get_history_summary
        result = get_history_summary(metric_type="system", hours=24)
        assert isinstance(result["data"], list)

    def test_count_matches_data_length(self) -> None:
        from app.metrics.dashboard import get_history_summary
        result = get_history_summary(metric_type="system", hours=24)
        assert result["count"] == len(result["data"])


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard API routes — routes.py
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboardAPIRoutes:

    # ── GET /dashboard/overview ───────────────────────────────────────────────

    def test_overview_returns_200(self) -> None:
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200

    def test_overview_success_flag(self) -> None:
        body = client.get("/api/v1/dashboard/overview").json()
        assert body["success"] is True

    def test_overview_data_has_required_keys(self) -> None:
        data = client.get("/api/v1/dashboard/overview").json()["data"]
        for key in ("timestamp", "system", "inference", "training", "alerts"):
            assert key in data, f"Missing key in overview: {key}"

    def test_overview_alerts_is_list(self) -> None:
        data = client.get("/api/v1/dashboard/overview").json()["data"]
        assert isinstance(data["alerts"], list)

    # ── GET /dashboard/system ─────────────────────────────────────────────────

    def test_system_returns_200(self) -> None:
        assert client.get("/api/v1/dashboard/system").status_code == 200

    def test_system_success_flag(self) -> None:
        assert client.get("/api/v1/dashboard/system").json()["success"] is True

    def test_system_data_has_cpu_percent(self) -> None:
        data = client.get("/api/v1/dashboard/system").json()["data"]
        assert "cpu_percent" in data

    def test_system_data_has_gpu_available(self) -> None:
        data = client.get("/api/v1/dashboard/system").json()["data"]
        assert "gpu_available" in data
        assert isinstance(data["gpu_available"], bool)

    def test_system_data_has_uptime(self) -> None:
        data = client.get("/api/v1/dashboard/system").json()["data"]
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_system_data_has_timestamp(self) -> None:
        data = client.get("/api/v1/dashboard/system").json()["data"]
        assert "timestamp" in data

    # ── GET /dashboard/inference ──────────────────────────────────────────────

    def test_inference_returns_200(self) -> None:
        assert client.get("/api/v1/dashboard/inference").status_code == 200

    def test_inference_success_flag(self) -> None:
        assert client.get("/api/v1/dashboard/inference").json()["success"] is True

    def test_inference_data_has_required_keys(self) -> None:
        data = client.get("/api/v1/dashboard/inference").json()["data"]
        for key in ("total_predictions", "succeeded", "failed", "success_rate",
                    "class_distribution", "confidence_distribution", "recent_predictions"):
            assert key in data, f"Missing key: {key}"

    def test_inference_total_predictions_is_int(self) -> None:
        data = client.get("/api/v1/dashboard/inference").json()["data"]
        assert isinstance(data["total_predictions"], int)

    def test_inference_confidence_distribution_structure(self) -> None:
        dist = client.get("/api/v1/dashboard/inference").json()["data"]["confidence_distribution"]
        assert "buckets" in dist
        assert "counts" in dist
        assert len(dist["buckets"]) == len(dist["counts"])

    # ── GET /dashboard/training ───────────────────────────────────────────────

    def test_training_returns_200(self) -> None:
        assert client.get("/api/v1/dashboard/training").status_code == 200

    def test_training_success_flag(self) -> None:
        assert client.get("/api/v1/dashboard/training").json()["success"] is True

    def test_training_data_has_required_keys(self) -> None:
        data = client.get("/api/v1/dashboard/training").json()["data"]
        for key in ("total_jobs", "running_jobs", "completed_jobs", "failed_jobs",
                    "recent_jobs", "recent_experiments"):
            assert key in data, f"Missing key: {key}"

    def test_training_job_counts_non_negative(self) -> None:
        data = client.get("/api/v1/dashboard/training").json()["data"]
        for k in ("total_jobs", "running_jobs", "completed_jobs", "failed_jobs"):
            assert data[k] >= 0

    # ── GET /dashboard/history ────────────────────────────────────────────────

    def test_history_returns_200_default(self) -> None:
        assert client.get("/api/v1/dashboard/history").status_code == 200

    def test_history_system_type(self) -> None:
        resp = client.get("/api/v1/dashboard/history?metric_type=system&hours=1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["metric_type"] == "system"

    def test_history_inference_type(self) -> None:
        resp = client.get("/api/v1/dashboard/history?metric_type=inference&hours=6")
        assert resp.status_code == 200
        assert resp.json()["data"]["metric_type"] == "inference"

    def test_history_training_type(self) -> None:
        resp = client.get("/api/v1/dashboard/history?metric_type=training")
        assert resp.status_code == 200

    def test_history_overview_type(self) -> None:
        resp = client.get("/api/v1/dashboard/history?metric_type=overview")
        assert resp.status_code == 200

    def test_history_invalid_type_returns_422(self) -> None:
        resp = client.get("/api/v1/dashboard/history?metric_type=badtype")
        assert resp.status_code == 422

    def test_history_data_has_count_and_list(self) -> None:
        data = client.get("/api/v1/dashboard/history?metric_type=system").json()["data"]
        assert "count" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_history_count_matches_data_length(self) -> None:
        data = client.get("/api/v1/dashboard/history?metric_type=system").json()["data"]
        assert data["count"] == len(data["data"])

    def test_history_hours_out_of_range_clamped(self) -> None:
        # hours > 168 should be clamped — no error
        resp = client.get("/api/v1/dashboard/history?metric_type=system&hours=9999")
        assert resp.status_code == 200
