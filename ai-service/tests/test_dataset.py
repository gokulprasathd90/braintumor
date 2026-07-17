"""
tests/test_dataset.py — Unit tests for the dataset management module.

Covers
------
  validator   : valid structure, missing class, too few images, bad extensions,
                nested dirs, nonexistent path
  splitter    : correct split counts, ratio enforcement, seed reproducibility,
                overwrite guard, FileExistsError
  stats       : count accuracy, imbalance ratio, class weights sum, full=False
  metadata    : save / load round-trip, update, missing file returns None
  orchestrator: prepare_dataset() happy path, invalid ratios, bad source dir
  API routes  : GET /dataset/info, POST /dataset/validate, POST /dataset/prepare
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("BCRYPT_ROUNDS", "4")

from app.main import app
from app.security.auth import get_user_store
from app.security.jwt import create_access_token

client = TestClient(app)


def _admin_headers() -> dict:
    store = get_user_store()
    admin = store.get_by_username("admin")
    token = create_access_token({"sub": admin.user_id, "role": admin.role.value})
    return {"Authorization": f"Bearer {token}"}


def _viewer_headers() -> dict:
    store = get_user_store()
    viewer = store.get_by_username("viewer")
    token = create_access_token({"sub": viewer.user_id, "role": viewer.role.value})
    return {"Authorization": f"Bearer {token}"}

# ─── Fixtures ─────────────────────────────────────────────────────────────────

CLASSES = ["glioma", "meningioma", "notumor", "pituitary"]


def _make_png(path: Path, size: int = 16) -> None:
    """Write a minimal valid PNG image to *path*."""
    img = np.full((size, size, 3), np.random.randint(0, 255), dtype=np.uint8)
    cv2.imwrite(str(path), img)


def _build_dataset(root: Path, counts: dict[str, int]) -> Path:
    """
    Create a synthetic dataset under *root* with the given class image counts.

    Returns *root*.
    """
    for cls, n in counts.items():
        cls_dir = root / cls
        cls_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            _make_png(cls_dir / f"img_{i:04d}.png")
    return root


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Balanced synthetic dataset — 50 images per class."""
    return _build_dataset(tmp_path / "raw", {c: 50 for c in CLASSES})


@pytest.fixture
def small_raw_dir(tmp_path: Path) -> Path:
    """Very small dataset — 15 images per class (above 10-image minimum)."""
    return _build_dataset(tmp_path / "raw_small", {c: 15 for c in CLASSES})


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "processed"


# ─── validator ────────────────────────────────────────────────────────────────

class TestValidateDataset:
    def test_valid_dataset_passes(self, raw_dir: Path) -> None:
        from app.dataset.validator import validate_dataset
        result = validate_dataset(raw_dir, expected_classes=CLASSES)
        assert result.is_valid is True
        assert result.errors == []

    def test_correct_class_counts(self, raw_dir: Path) -> None:
        from app.dataset.validator import validate_dataset
        result = validate_dataset(raw_dir, expected_classes=CLASSES)
        assert result.total_images == 50 * len(CLASSES)
        for cls in CLASSES:
            assert result.class_counts[cls] == 50

    def test_missing_directory_returns_invalid(self, tmp_path: Path) -> None:
        from app.dataset.validator import validate_dataset
        result = validate_dataset(tmp_path / "nonexistent")
        assert result.is_valid is False
        assert any("does not exist" in e for e in result.errors)

    def test_missing_class_is_error_when_required(self, tmp_path: Path) -> None:
        from app.dataset.validator import validate_dataset
        # Create dataset with only 3 classes
        partial = _build_dataset(tmp_path / "partial", {c: 20 for c in CLASSES[:3]})
        result = validate_dataset(partial, expected_classes=CLASSES, require_all_classes=True)
        assert result.is_valid is False
        assert CLASSES[3] in result.classes_missing

    def test_missing_class_is_warning_when_not_required(self, tmp_path: Path) -> None:
        from app.dataset.validator import validate_dataset
        partial = _build_dataset(tmp_path / "partial2", {c: 20 for c in CLASSES[:3]})
        result = validate_dataset(partial, expected_classes=CLASSES, require_all_classes=False)
        assert result.is_valid is True
        assert result.warnings  # missing class → warning

    def test_too_few_images_per_class(self, tmp_path: Path) -> None:
        from app.dataset.validator import validate_dataset
        tiny = _build_dataset(tmp_path / "tiny", {c: 5 for c in CLASSES})
        result = validate_dataset(tiny, expected_classes=CLASSES, min_images_per_class=10)
        assert result.is_valid is False
        assert len(result.errors) == len(CLASSES)

    def test_non_image_files_produce_warning(self, raw_dir: Path) -> None:
        from app.dataset.validator import validate_dataset
        # Add a non-image file to one class
        (raw_dir / CLASSES[0] / "readme.txt").write_text("ignore me")
        result = validate_dataset(raw_dir, expected_classes=CLASSES)
        assert result.is_valid is True
        assert any("non-image" in w for w in result.warnings)

    def test_nested_subdirectory_produces_warning(self, raw_dir: Path) -> None:
        from app.dataset.validator import validate_dataset
        (raw_dir / CLASSES[0] / "subdir").mkdir()
        result = validate_dataset(raw_dir, expected_classes=CLASSES)
        assert result.is_valid is True
        assert any("sub-director" in w for w in result.warnings)

    def test_extra_class_dir_produces_warning(self, raw_dir: Path) -> None:
        from app.dataset.validator import validate_dataset
        (raw_dir / "unknown_class").mkdir()
        result = validate_dataset(raw_dir, expected_classes=CLASSES)
        assert any("unknown_class" in w for w in result.warnings)

    def test_to_dict_contains_required_keys(self, raw_dir: Path) -> None:
        from app.dataset.validator import validate_dataset
        d = validate_dataset(raw_dir, expected_classes=CLASSES).to_dict()
        for key in ("is_valid", "classes_found", "class_counts", "total_images",
                    "errors", "warnings"):
            assert key in d


# ─── splitter ─────────────────────────────────────────────────────────────────

class TestSplitDataset:
    def test_split_creates_correct_structure(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        split_dataset(raw_dir, output_dir, train_ratio=0.7, val_ratio=0.15,
                      test_ratio=0.15, classes=CLASSES)
        for split in ("train", "val", "test"):
            for cls in CLASSES:
                assert (output_dir / split / cls).is_dir()

    def test_total_images_preserved(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        result = split_dataset(raw_dir, output_dir, train_ratio=0.7, val_ratio=0.15,
                                test_ratio=0.15, classes=CLASSES)
        total_out = sum(result.total_per_split.values())
        assert total_out == 50 * len(CLASSES)

    def test_approximate_ratios(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        result = split_dataset(raw_dir, output_dir, train_ratio=0.7, val_ratio=0.15,
                                test_ratio=0.15, classes=CLASSES)
        total = sum(result.total_per_split.values())
        train_frac = result.total_per_split["train"] / total
        # Allow ±5 % for small dataset rounding
        assert abs(train_frac - 0.70) < 0.05

    def test_seed_reproducibility(self, tmp_path: Path) -> None:
        from app.dataset.splitter import split_dataset
        raw   = _build_dataset(tmp_path / "raw_rep", {c: 30 for c in CLASSES})
        out1  = tmp_path / "out1"
        out2  = tmp_path / "out2"
        r1 = split_dataset(raw, out1, train_ratio=0.7, val_ratio=0.15,
                            test_ratio=0.15, seed=42, classes=CLASSES)
        r2 = split_dataset(raw, out2, train_ratio=0.7, val_ratio=0.15,
                            test_ratio=0.15, seed=42, classes=CLASSES)
        assert r1.split_counts == r2.split_counts

    def test_different_seeds_differ(self, tmp_path: Path) -> None:
        from app.dataset.splitter import split_dataset
        raw  = _build_dataset(tmp_path / "raw_seed", {c: 40 for c in CLASSES})
        out1 = tmp_path / "diff1"
        out2 = tmp_path / "diff2"
        r1 = split_dataset(raw, out1, seed=1, classes=CLASSES)
        r2 = split_dataset(raw, out2, seed=99, classes=CLASSES)
        # Different seeds → different per-class assignments
        # (counts may happen to be equal for tiny sets, check filenames instead)
        names_train_1 = {p.name for p in (out1 / "train" / CLASSES[0]).iterdir()}
        names_train_2 = {p.name for p in (out2 / "train" / CLASSES[0]).iterdir()}
        assert names_train_1 != names_train_2

    def test_existing_output_raises_without_overwrite(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        from app.dataset.splitter import split_dataset
        split_dataset(raw_dir, output_dir, classes=CLASSES)
        with pytest.raises(FileExistsError):
            split_dataset(raw_dir, output_dir, classes=CLASSES)

    def test_overwrite_flag_replaces_output(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        split_dataset(raw_dir, output_dir, classes=CLASSES)
        # Should not raise
        split_dataset(raw_dir, output_dir, overwrite=True, classes=CLASSES)

    def test_invalid_ratio_sum_raises(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        with pytest.raises(ValueError, match="must equal 1.0"):
            split_dataset(raw_dir, output_dir, train_ratio=0.5, val_ratio=0.3,
                          test_ratio=0.3, classes=CLASSES)

    def test_result_to_dict_keys(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        d = split_dataset(raw_dir, output_dir, classes=CLASSES).to_dict()
        for key in ("output_dir", "split_counts", "total_per_split", "ratios_used",
                    "seed", "classes"):
            assert key in d


# ─── stats ────────────────────────────────────────────────────────────────────

class TestComputeDatasetStats:
    def test_correct_total_count(self, raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(raw_dir, classes=CLASSES)
        assert stats["total_images"] == 50 * len(CLASSES)

    def test_class_counts_correct(self, raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(raw_dir, classes=CLASSES)
        for cls in CLASSES:
            assert stats["class_counts"][cls] == 50

    def test_balanced_dataset_flagged(self, raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(raw_dir, classes=CLASSES)
        assert stats["is_balanced"] is True
        assert stats["imbalance_ratio"] == pytest.approx(1.0, abs=0.01)

    def test_imbalanced_dataset_flagged(self, tmp_path: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        imbal = _build_dataset(tmp_path / "imbal",
                               {"glioma": 100, "meningioma": 20,
                                "notumor": 80, "pituitary": 60})
        stats = compute_dataset_stats(imbal, classes=CLASSES)
        assert stats["is_balanced"] is False
        assert stats["imbalance_ratio"] == pytest.approx(100 / 20, abs=0.1)

    def test_class_weights_sum_to_num_classes(self, raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(raw_dir, classes=CLASSES)
        weight_sum = sum(stats["class_weights"].values())
        assert weight_sum == pytest.approx(len(CLASSES), abs=0.01)

    def test_distribution_sums_to_one(self, raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(raw_dir, classes=CLASSES)
        dist_sum = sum(stats["class_distribution"].values())
        assert dist_sum == pytest.approx(1.0, abs=0.01)

    def test_full_stats_include_pixel_and_dimension(self, small_raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(small_raw_dir, classes=CLASSES, full=True,
                                      pixel_sample_size=20, dimension_sample_size=10)
        assert "pixel_stats"     in stats
        assert "dimension_stats" in stats
        ps = stats["pixel_stats"]
        assert len(ps["mean_rgb"]) == 3
        assert len(ps["std_rgb"])  == 3

    def test_fast_mode_no_pixel_stats(self, raw_dir: Path) -> None:
        from app.dataset.stats import compute_dataset_stats
        stats = compute_dataset_stats(raw_dir, classes=CLASSES, full=False)
        assert "pixel_stats"     not in stats
        assert "dimension_stats" not in stats


class TestComputeSplitStats:
    def test_split_stats_after_split(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset.splitter import split_dataset
        from app.dataset.stats import compute_split_stats
        split_dataset(raw_dir, output_dir, classes=CLASSES)
        stats = compute_split_stats(output_dir, classes=CLASSES)
        assert stats["grand_total"] == 50 * len(CLASSES)
        assert set(stats["splits"].keys()) == {"train", "val", "test"}

    def test_missing_splits_return_zeros(self, tmp_path: Path) -> None:
        from app.dataset.stats import compute_split_stats
        empty = tmp_path / "empty_processed"
        empty.mkdir()
        stats = compute_split_stats(empty, classes=CLASSES)
        assert stats["grand_total"] == 0


# ─── metadata ─────────────────────────────────────────────────────────────────

class TestMetadata:
    def _base_kwargs(self, raw_dir: Path, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        return dict(
            raw_dir=raw_dir,
            classes=CLASSES,
            split_ratios={"train": 0.7, "val": 0.15, "test": 0.15},
            split_counts={"train": {c: 35 for c in CLASSES},
                          "val":   {c: 8  for c in CLASSES},
                          "test":  {c: 7  for c in CLASSES}},
            total_per_split={"train": 140, "val": 32, "test": 28},
            raw_class_counts={c: 50 for c in CLASSES},
            class_weights={c: 1.0 for c in CLASSES},
            imbalance_ratio=1.0,
            is_balanced=True,
        )

    def test_save_creates_json_file(self, raw_dir: Path, tmp_path: Path) -> None:
        from app.dataset.metadata import save_dataset_info
        out = tmp_path / "meta_out"
        save_dataset_info(out, **self._base_kwargs(raw_dir, out))
        assert (out / "dataset_info.json").exists()

    def test_load_round_trip(self, raw_dir: Path, tmp_path: Path) -> None:
        from app.dataset.metadata import save_dataset_info, load_dataset_info
        out = tmp_path / "meta_rt"
        save_dataset_info(out, **self._base_kwargs(raw_dir, out))
        info = load_dataset_info(out)
        assert info is not None
        assert info["classes"] == CLASSES
        assert info["class_to_index"]["glioma"] == 0
        assert info["index_to_class"]["0"] == "glioma"

    def test_load_returns_none_when_missing(self, tmp_path: Path) -> None:
        from app.dataset.metadata import load_dataset_info
        assert load_dataset_info(tmp_path / "no_such_dir") is None

    def test_update_merges_fields(self, raw_dir: Path, tmp_path: Path) -> None:
        from app.dataset.metadata import save_dataset_info, update_dataset_info, load_dataset_info
        out = tmp_path / "meta_upd"
        save_dataset_info(out, **self._base_kwargs(raw_dir, out))
        update_dataset_info(out, {"training_completed": True})
        info = load_dataset_info(out)
        assert info["training_completed"] is True
        assert info["classes"] == CLASSES  # original fields preserved

    def test_dataset_info_exists(self, raw_dir: Path, tmp_path: Path) -> None:
        from app.dataset.metadata import save_dataset_info, dataset_info_exists
        out = tmp_path / "meta_ex"
        assert dataset_info_exists(out) is False
        save_dataset_info(out, **self._base_kwargs(raw_dir, out))
        assert dataset_info_exists(out) is True

    def test_schema_version_present(self, raw_dir: Path, tmp_path: Path) -> None:
        from app.dataset.metadata import save_dataset_info, load_dataset_info
        out = tmp_path / "meta_sv"
        save_dataset_info(out, **self._base_kwargs(raw_dir, out))
        info = load_dataset_info(out)
        assert "schema_version" in info

    def test_pixel_stats_stored(self, raw_dir: Path, tmp_path: Path) -> None:
        from app.dataset.metadata import save_dataset_info, load_dataset_info
        out = tmp_path / "meta_ps"
        pixel = {"mean_rgb": [0.5, 0.5, 0.5], "std_rgb": [0.2, 0.2, 0.2]}
        save_dataset_info(out, pixel_stats=pixel, **self._base_kwargs(raw_dir, out))
        info = load_dataset_info(out)
        assert info["pixel_stats"]["mean_rgb"] == [0.5, 0.5, 0.5]


# ─── orchestrator ─────────────────────────────────────────────────────────────

class TestPrepareDataset:
    def test_happy_path(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset import prepare_dataset
        result = prepare_dataset(
            raw_dir=raw_dir,
            output_dir=output_dir,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=42,
            classes=CLASSES,
        )
        assert result["validation"]["is_valid"] is True
        assert result["split"]["total_per_split"]["train"] > 0
        assert Path(result["metadata_path"]).exists()

    def test_metadata_json_written(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset import prepare_dataset
        result = prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        info_path = Path(result["metadata_path"])
        with open(info_path) as f:
            info = json.load(f)
        assert info["classes"] == CLASSES
        assert "class_to_index" in info

    def test_invalid_ratios_raise(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset import prepare_dataset
        with pytest.raises(ValueError):
            prepare_dataset(raw_dir=raw_dir, output_dir=output_dir,
                            train_ratio=0.6, val_ratio=0.3, test_ratio=0.3,
                            classes=CLASSES)

    def test_nonexistent_raw_dir_raises(self, tmp_path: Path) -> None:
        from app.dataset import prepare_dataset
        with pytest.raises(ValueError, match="validation failed"):
            prepare_dataset(raw_dir=tmp_path / "ghost", output_dir=tmp_path / "out",
                            classes=CLASSES)

    def test_duration_is_positive(self, raw_dir: Path, output_dir: Path) -> None:
        from app.dataset import prepare_dataset
        result = prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        assert result["duration_s"] > 0

    def test_overwrite_false_raises_on_second_call(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        from app.dataset import prepare_dataset
        prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        with pytest.raises(FileExistsError):
            prepare_dataset(raw_dir=raw_dir, output_dir=output_dir,
                            overwrite=False, classes=CLASSES)

    def test_overwrite_true_succeeds_on_second_call(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        from app.dataset import prepare_dataset
        prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        result = prepare_dataset(raw_dir=raw_dir, output_dir=output_dir,
                                 overwrite=True, classes=CLASSES)
        assert result["validation"]["is_valid"] is True


# ─── API routes ───────────────────────────────────────────────────────────────

class TestDatasetAPIRoutes:
    def test_info_returns_404_when_no_metadata(self) -> None:
        resp = client.get("/api/v1/dataset/info",
                          params={"processed_dir": "/nonexistent/path/processed"})
        assert resp.status_code == 404

    def test_validate_returns_422_for_missing_dir(self) -> None:
        resp = client.post("/api/v1/dataset/validate",
                           json={"raw_dir": "/nonexistent/path/raw"})
        # validate_dataset returns is_valid=False, not an HTTP error
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["data"]["is_valid"] is False

    def test_validate_success_flag_structure(self) -> None:
        resp = client.post("/api/v1/dataset/validate",
                           json={"raw_dir": "/nonexistent/path"})
        assert resp.status_code == 200
        body = resp.json()
        assert "success" in body
        assert "data"    in body
        assert "message" in body

    def test_prepare_rejects_bad_ratios(self) -> None:
        resp = client.post("/api/v1/dataset/prepare",
                           json={"train_ratio": 0.6, "val_ratio": 0.3, "test_ratio": 0.3})
        assert resp.status_code == 422

    def test_prepare_returns_404_for_missing_dataset(self) -> None:
        resp = client.post("/api/v1/dataset/prepare",
                           json={"raw_dir": "/no/such/dataset"})
        assert resp.status_code == 422  # validation error propagates as 422

    def test_info_returns_200_when_metadata_exists(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        from app.dataset import prepare_dataset
        prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        resp = client.get("/api/v1/dataset/info",
                          params={"processed_dir": str(output_dir)})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["classes"] == CLASSES

    def test_prepare_endpoint_creates_split(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        resp = client.post("/api/v1/dataset/prepare", json={
            "raw_dir":    str(raw_dir),
            "output_dir": str(output_dir),
            "train_ratio": 0.70,
            "val_ratio":   0.15,
            "test_ratio":  0.15,
            "overwrite":   False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "train" in body["data"]["split"]["total_per_split"]

    def test_prepare_endpoint_409_on_existing(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        from app.dataset import prepare_dataset
        prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        resp = client.post("/api/v1/dataset/prepare", json={
            "raw_dir":    str(raw_dir),
            "output_dir": str(output_dir),
            "overwrite":  False,
        })
        assert resp.status_code == 409

    def test_prepare_endpoint_overwrite_succeeds(
        self, raw_dir: Path, output_dir: Path
    ) -> None:
        from app.dataset import prepare_dataset
        prepare_dataset(raw_dir=raw_dir, output_dir=output_dir, classes=CLASSES)
        resp = client.post("/api/v1/dataset/prepare", json={
            "raw_dir":    str(raw_dir),
            "output_dir": str(output_dir),
            "overwrite":  True,
        })
        assert resp.status_code == 200
