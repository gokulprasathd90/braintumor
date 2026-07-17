"""
app/inference/batch.py — BatchInferenceRunner: parallel batch prediction
with progress tracking, CSV/JSON export, and failure reporting.

Wraps ``InferencePipeline`` with:
  - Thread-pool parallelism (configurable max_workers).
  - Per-item timeout handling.
  - Progress callback support.
  - CSV export (flat row per image).
  - JSON export (full nested structure).
  - Failure isolation (one bad image never stops the batch).

Usage
-----
    from app.inference.batch import BatchInferenceRunner
    from app.inference.config import InferenceConfig

    cfg    = InferenceConfig(model_name="efficientnet", max_workers=4)
    runner = BatchInferenceRunner(cfg)

    # From a directory
    result = runner.run_directory("dataset/test/glioma/")

    # From a ZIP
    result = runner.run_zip("images.zip")

    # Export results
    paths = runner.export(result, output_dir="output/", formats=("json", "csv"))
"""

from __future__ import annotations

import csv
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.inference.config import InferenceConfig, DEFAULT_INFERENCE_CONFIG
from app.inference.pipeline import InferencePipeline
from app.inference.results import (
    BatchItemResult,
    BatchPredictionResult,
    PredictionResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# BatchInferenceRunner
# ─────────────────────────────────────────────────────────────────────────────

class BatchInferenceRunner:
    """
    Parallel batch inference with export and progress tracking.

    Parameters
    ----------
    cfg : InferenceConfig | None
        Inference configuration.  Defaults to ``DEFAULT_INFERENCE_CONFIG``.
    progress_callback : callable | None
        Called after each item with ``(completed: int, total: int)``.
        Useful for streaming progress to a websocket or logging.
    """

    def __init__(
        self,
        cfg: Optional[InferenceConfig] = None,
        *,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        self.cfg               = cfg or DEFAULT_INFERENCE_CONFIG
        self.pipeline          = InferencePipeline(cfg)
        self.progress_callback = progress_callback

    # ─────────────────────────────────────────────────────────────────────────
    # Core runner
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        sources: List[Tuple[str, Any]],
        *,
        source_type: str = "list",
    ) -> BatchPredictionResult:
        """
        Run inference on a list of (filename, source) tuples in parallel.

        Parameters
        ----------
        sources : list[tuple[str, source]]
            Each element is (display_filename, image_source).
            image_source may be a file path (str/Path) or raw bytes.
        source_type : str
            Label for the result ("directory" | "zip" | "list").

        Returns
        -------
        BatchPredictionResult
        """
        if not sources:
            return BatchPredictionResult(
                total=0, succeeded=0, failed=0,
                results=[], timing_ms=0.0,
                model_name=self.cfg.model_name,
                source_type=source_type,
            )

        total = len(sources)
        items: List[BatchItemResult] = [None] * total  # type: ignore[list-item]
        succeeded = 0
        failed = 0
        completed = 0
        t0 = time.perf_counter()

        # Pre-warm model (serial load on first use) before entering thread pool
        # so all workers share the same cached model.
        from app.inference.cache import get_model
        get_model(self.cfg.model_name)

        def _predict_one(idx_filename_source: Tuple[int, str, Any]) -> Tuple[int, BatchItemResult]:
            idx, filename, source = idx_filename_source
            img_id = str(uuid.uuid4())
            try:
                result = self.pipeline.predict(
                    source,
                    image_id=img_id,
                    source_path=filename,
                )
                return idx, BatchItemResult(filename=filename, success=True, result=result)
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
                logger.warning(f"[BatchRunner] Failed '{filename}': {err}")
                return idx, BatchItemResult(filename=filename, success=False, error=err)

        with ThreadPoolExecutor(max_workers=self.cfg.max_workers) as executor:
            tasks = [(i, fname, src) for i, (fname, src) in enumerate(sources)]
            timeout = self.cfg.timeout_s if self.cfg.timeout_s > 0 else None

            futures = {executor.submit(_predict_one, t): t[0] for t in tasks}

            for future in futures:  # completed order varies but we re-index
                try:
                    idx, item = future.result(timeout=timeout)
                except FuturesTimeout:
                    idx = futures[future]
                    fname = tasks[idx][1]
                    err = f"TimeoutError: exceeded {self.cfg.timeout_s}s"
                    item = BatchItemResult(filename=fname, success=False, error=err)
                    logger.warning(f"[BatchRunner] Timeout '{fname}'")
                except Exception as exc:
                    idx = futures[future]
                    fname = tasks[idx][1]
                    err = f"{type(exc).__name__}: {exc}"
                    item = BatchItemResult(filename=fname, success=False, error=err)

                items[idx] = item
                if item.success:
                    succeeded += 1
                else:
                    failed += 1

                completed += 1
                if self.progress_callback:
                    try:
                        self.progress_callback(completed, total)
                    except Exception:
                        pass

        timing_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"[BatchRunner] Done | total={total} ok={succeeded} "
            f"fail={failed} ms={timing_ms:.1f}"
        )

        return BatchPredictionResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            results=items,
            timing_ms=round(timing_ms, 2),
            model_name=self.cfg.model_name,
            source_type=source_type,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Directory and ZIP entry points
    # ─────────────────────────────────────────────────────────────────────────

    def run_directory(
        self,
        directory: str | Path,
        *,
        extensions: tuple = (".jpg", ".jpeg", ".png", ".bmp"),
    ) -> BatchPredictionResult:
        """
        Run inference on all image files in *directory*.

        Raises
        ------
        FileNotFoundError
            When the directory does not exist.
        ValueError
            When no image files are found.
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        image_files = sorted([
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in extensions
        ])

        if not image_files:
            raise ValueError(
                f"No image files found in {directory} (extensions: {extensions})"
            )

        logger.info(
            f"[BatchRunner] Directory run | path={directory} "
            f"images={len(image_files)} workers={self.cfg.max_workers}"
        )
        sources = [(p.name, p) for p in image_files]
        return self.run(sources, source_type="directory")

    def run_zip(self, zip_path: str | Path) -> BatchPredictionResult:
        """
        Run inference on all images inside a ZIP archive.

        Raises
        ------
        FileNotFoundError
            When the ZIP file does not exist.
        ValueError
            When no image files are found in the archive.
        """
        import zipfile

        zip_path = Path(zip_path)
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        sources: List[Tuple[str, bytes]] = []

        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for name in sorted(zf.namelist()):
                suffix = Path(name).suffix.lower()
                if suffix in image_extensions and not name.startswith("__MACOSX"):
                    try:
                        data = zf.read(name)
                        sources.append((name, data))
                    except Exception as exc:
                        logger.warning(
                            f"[BatchRunner] Could not read '{name}' from ZIP: {exc}"
                        )

        if not sources:
            raise ValueError(f"No image files found in ZIP: {zip_path}")

        logger.info(
            f"[BatchRunner] ZIP run | path={zip_path} "
            f"images={len(sources)} workers={self.cfg.max_workers}"
        )
        return self.run(sources, source_type="zip")

    # ─────────────────────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────────────────────

    def export(
        self,
        result: BatchPredictionResult,
        *,
        output_dir: Optional[str | Path] = None,
        formats: Tuple[str, ...] = ("json",),
        stem: str = "batch_results",
    ) -> Dict[str, str]:
        """
        Export a BatchPredictionResult to disk.

        Parameters
        ----------
        result : BatchPredictionResult
        output_dir : str | Path | None
            Target directory (defaults to cfg.resolved_output_dir).
        formats : tuple
            Any combination of "json" and/or "csv".
        stem : str
            Base filename without extension.

        Returns
        -------
        dict
            {"json_path": str, "csv_path": str} — only keys whose format
            was requested are included.
        """
        out_dir = Path(output_dir) if output_dir else self.cfg.resolved_output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        paths: Dict[str, str] = {}

        if "json" in formats:
            json_path = out_dir / f"{stem}.json"
            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(result.to_dict(), fh, indent=2)
            paths["json_path"] = str(json_path)
            logger.info(f"[BatchRunner] JSON exported → {json_path}")

        if "csv" in formats:
            csv_path = out_dir / f"{stem}.csv"
            self._write_csv(result, csv_path)
            paths["csv_path"] = str(csv_path)
            logger.info(f"[BatchRunner] CSV exported → {csv_path}")

        # Attach export paths to the result object
        result.export_paths.update(paths)
        return paths

    @staticmethod
    def _write_csv(result: BatchPredictionResult, path: Path) -> None:
        """Write a flat CSV with one row per image."""
        fieldnames = [
            "filename", "success", "error",
            "image_id", "predicted_class", "predicted_class_index",
            "confidence", "is_high_confidence",
            "timing_ms", "model_name", "gradcam_path",
        ]

        # Dynamically add probability columns from the first successful result
        class_names: List[str] = []
        for item in result.results:
            if item.success and item.result:
                class_names = list(item.result.probabilities.keys())
                break
        fieldnames += [f"prob_{c}" for c in class_names]

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in result.results:
                row: Dict[str, Any] = {
                    "filename": item.filename,
                    "success":  item.success,
                    "error":    item.error or "",
                }
                if item.success and item.result:
                    r = item.result
                    row.update({
                        "image_id":              r.image_id,
                        "predicted_class":       r.predicted_class,
                        "predicted_class_index": r.predicted_class_index,
                        "confidence":            r.confidence,
                        "is_high_confidence":    r.is_high_confidence,
                        "timing_ms":             r.timing_ms,
                        "model_name":            r.metadata.model_name,
                        "gradcam_path":          r.metadata.gradcam_path or "",
                    })
                    for cls in class_names:
                        row[f"prob_{cls}"] = r.probabilities.get(cls, 0.0)
                writer.writerow(row)
