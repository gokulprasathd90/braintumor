"""
app/inference/pipeline.py — InferencePipeline: production single-image and
batch inference with optional Grad-CAM, timing, and top-K results.

The pipeline is the primary entry point for all inference in the system.
It wraps preprocessing, model execution, and result assembly into a
clean, testable class that operates independently of FastAPI.

Usage — Python
--------------
    from app.inference.pipeline import InferencePipeline
    from app.inference.config import InferenceConfig

    pipeline = InferencePipeline()
    result   = pipeline.predict(image_bytes)
    print(result.predicted_class, result.confidence)

    # Custom config
    cfg      = InferenceConfig(model_name="resnet50", top_k=3, generate_gradcam=True)
    pipeline = InferencePipeline(cfg)
    result   = pipeline.predict(open("scan.jpg", "rb").read())

Usage — CLI
-----------
    python -m app.inference.pipeline scan.jpg
    python -m app.inference.pipeline scan.jpg --model resnet50 --top-k 3
    python -m app.inference.pipeline scan.jpg --gradcam
    python -m app.inference.pipeline --batch dataset/test/
    python -m app.inference.pipeline --zip images.zip
"""

from __future__ import annotations

import argparse
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.inference.cache import get_model, list_available_models
from app.inference.config import InferenceConfig, DEFAULT_INFERENCE_CONFIG
from app.inference.results import (
    BatchItemResult,
    BatchPredictionResult,
    PredictionMetadata,
    PredictionResult,
    TopKPrediction,
)


class InferencePipeline:
    """
    Production inference pipeline for single-image and batch prediction.

    Parameters
    ----------
    cfg : InferenceConfig | None
        Pipeline configuration.  Defaults to ``DEFAULT_INFERENCE_CONFIG``.
    """

    def __init__(self, cfg: Optional[InferenceConfig] = None) -> None:
        self.cfg = cfg or DEFAULT_INFERENCE_CONFIG

    # ─────────────────────────────────────────────────────────────────────────
    # Single-image inference
    # ─────────────────────────────────────────────────────────────────────────

    def predict(
        self,
        source: str | bytes | Path,
        *,
        image_id: Optional[str] = None,
        source_path: Optional[str] = None,
    ) -> PredictionResult:
        """
        Run inference on a single image.

        Parameters
        ----------
        source : str | bytes | Path
            File path or raw JPEG/PNG bytes.
        image_id : str | None
            Caller-supplied ID.  A UUID is generated when None.
        source_path : str | None
            Original filesystem path (for metadata in batch scenarios).

        Returns
        -------
        PredictionResult
            Full prediction with probabilities, top-K, timing, and optional
            Grad-CAM path.

        Raises
        ------
        FileNotFoundError
            When no saved weights exist for the configured model.
        ValueError
            When the image cannot be decoded.
        """
        img_id = image_id or str(uuid.uuid4())
        t0 = time.perf_counter()

        try:
            result = self._predict_single(source, img_id, source_path)
        except Exception as exc:
            timing_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                f"[Pipeline] Prediction failed for {img_id}: {exc}"
            )
            raise

        timing_ms = (time.perf_counter() - t0) * 1000
        # Patch timing (was set to 0.0 during assembly)
        return PredictionResult(
            image_id=result.image_id,
            predicted_class=result.predicted_class,
            predicted_class_index=result.predicted_class_index,
            confidence=result.confidence,
            is_high_confidence=result.is_high_confidence,
            probabilities=result.probabilities,
            top_k=result.top_k,
            timing_ms=round(timing_ms, 2),
            metadata=result.metadata,
            error=result.error,
        )

    def _predict_single(
        self,
        source: str | bytes | Path,
        image_id: str,
        source_path: Optional[str],
    ) -> PredictionResult:
        """Core prediction — no timing wrapper."""
        cfg = self.cfg

        # ── Load model ────────────────────────────────────────────────────────
        model = get_model(cfg.model_name)

        # ── Preprocess ────────────────────────────────────────────────────────
        from app.preprocessing.preprocess import preprocess_for_inference
        tensor: np.ndarray = preprocess_for_inference(source, expand_dims=True)

        # ── Inference ─────────────────────────────────────────────────────────
        raw_preds: np.ndarray = model.predict(tensor, verbose=0)
        probs: np.ndarray     = raw_preds[0]

        # ── Top-1 ─────────────────────────────────────────────────────────────
        top1_idx   = int(np.argmax(probs))
        top1_label = cfg.class_names[top1_idx]
        confidence = round(float(probs[top1_idx]), 4)

        # ── Probability distribution ──────────────────────────────────────────
        probabilities = {
            label: round(float(probs[i]), 4)
            for i, label in enumerate(cfg.class_names)
        }

        # ── Top-K ─────────────────────────────────────────────────────────────
        top_k_indices = np.argsort(probs)[::-1][: cfg.top_k]
        top_k = [
            TopKPrediction(
                rank=rank + 1,
                class_name=cfg.class_names[idx],
                class_index=int(idx),
                probability=round(float(probs[idx]), 4),
            )
            for rank, idx in enumerate(top_k_indices)
        ]

        # ── Grad-CAM (optional) ───────────────────────────────────────────────
        gradcam_path: Optional[str] = None
        if cfg.generate_gradcam:
            gradcam_path = self._run_gradcam(source, image_id, top1_idx)

        # ── Metadata ──────────────────────────────────────────────────────────
        from app.models.load_model import get_model_info
        model_info = get_model_info(cfg.model_name)

        metadata = PredictionMetadata(
            model_name=cfg.model_name,
            model_version=model_info.get("saved_at") or cfg.model_version,
            image_size=cfg.image_size,
            class_names=cfg.class_names,
            source_path=source_path,
            gradcam_path=gradcam_path,
        )

        logger.info(
            f"[Pipeline] {image_id} → {top1_label} ({confidence:.4f}) "
            f"model={cfg.model_name}"
        )

        return PredictionResult(
            image_id=image_id,
            predicted_class=top1_label,
            predicted_class_index=top1_idx,
            confidence=confidence,
            is_high_confidence=confidence >= cfg.confidence_threshold,
            probabilities=probabilities,
            top_k=top_k,
            timing_ms=0.0,      # patched by caller
            metadata=metadata,
            error=None,
        )

    def _run_gradcam(
        self,
        source: str | bytes | Path,
        image_id: str,
        class_index: int,
    ) -> Optional[str]:
        """Generate Grad-CAM, returning the output path or None on failure."""
        try:
            from app.utils.gradcam import generate_gradcam
            result = generate_gradcam(
                source,
                model_name=self.cfg.model_name,
                class_index=class_index,
                image_id=image_id,
                alpha=self.cfg.gradcam_alpha,
            )
            return result.get("gradcam_path")
        except Exception as exc:
            logger.warning(f"[Pipeline] Grad-CAM failed for {image_id}: {exc}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Batch inference — list of sources
    # ─────────────────────────────────────────────────────────────────────────

    def predict_batch(
        self,
        sources: List[tuple[str, str | bytes | Path]],
        *,
        source_type: str = "list",
    ) -> BatchPredictionResult:
        """
        Run inference on a list of (filename, source) tuples.

        Parameters
        ----------
        sources : list[tuple[str, str|bytes|Path]]
            Each element is (display_filename, image_source).
        source_type : str
            "directory" | "zip" | "list" (reported in result).

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

        t0 = time.perf_counter()
        items: List[BatchItemResult] = []
        succeeded = 0
        failed = 0

        for filename, source in sources:
            img_id = str(uuid.uuid4())
            try:
                result = self.predict(source, image_id=img_id, source_path=filename)
                items.append(BatchItemResult(
                    filename=filename, success=True, result=result
                ))
                succeeded += 1
            except Exception as exc:
                err_msg = f"{type(exc).__name__}: {exc}"
                logger.warning(f"[Pipeline] Batch item failed '{filename}': {err_msg}")
                items.append(BatchItemResult(
                    filename=filename, success=False, error=err_msg
                ))
                failed += 1

        timing_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"[Pipeline] Batch complete | total={len(sources)} "
            f"ok={succeeded} fail={failed} ms={timing_ms:.1f}"
        )

        return BatchPredictionResult(
            total=len(sources),
            succeeded=succeeded,
            failed=failed,
            results=items,
            timing_ms=round(timing_ms, 2),
            model_name=self.cfg.model_name,
            source_type=source_type,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Directory inference
    # ─────────────────────────────────────────────────────────────────────────

    def predict_directory(
        self,
        directory: str | Path,
        *,
        extensions: tuple = (".jpg", ".jpeg", ".png", ".bmp"),
    ) -> BatchPredictionResult:
        """
        Run inference on every image file in *directory*.

        Parameters
        ----------
        directory : str | Path
            Root directory to scan (non-recursive).
        extensions : tuple
            File extensions to include (lower-case).

        Returns
        -------
        BatchPredictionResult

        Raises
        ------
        FileNotFoundError
            When *directory* does not exist.
        ValueError
            When no image files are found.
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(
                f"Directory not found: {directory}"
            )

        image_files = sorted([
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in extensions
        ])

        if not image_files:
            raise ValueError(
                f"No image files found in {directory} "
                f"(extensions: {extensions})"
            )

        logger.info(
            f"[Pipeline] Directory batch | path={directory} "
            f"images={len(image_files)}"
        )

        sources = [(p.name, p) for p in image_files]
        return self.predict_batch(sources, source_type="directory")

    # ─────────────────────────────────────────────────────────────────────────
    # ZIP inference
    # ─────────────────────────────────────────────────────────────────────────

    def predict_zip(self, zip_path: str | Path) -> BatchPredictionResult:
        """
        Run inference on all images inside a ZIP archive.

        The ZIP file is read in-memory; no extraction to disk is required.

        Parameters
        ----------
        zip_path : str | Path
            Path to the ZIP file.

        Returns
        -------
        BatchPredictionResult

        Raises
        ------
        FileNotFoundError
            When *zip_path* does not exist.
        ValueError
            When no image files are found inside the ZIP.
        """
        import zipfile

        zip_path = Path(zip_path)
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        sources: List[tuple[str, bytes]] = []

        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for name in sorted(zf.namelist()):
                suffix = Path(name).suffix.lower()
                if suffix in image_extensions and not name.startswith("__MACOSX"):
                    try:
                        data = zf.read(name)
                        sources.append((name, data))
                    except Exception as exc:
                        logger.warning(
                            f"[Pipeline] Could not read '{name}' from ZIP: {exc}"
                        )

        if not sources:
            raise ValueError(
                f"No image files found in ZIP archive: {zip_path}"
            )

        logger.info(
            f"[Pipeline] ZIP batch | path={zip_path} images={len(sources)}"
        )

        return self.predict_batch(sources, source_type="zip")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience function
# ─────────────────────────────────────────────────────────────────────────────

def predict(
    source: str | bytes | Path,
    *,
    model_name: Optional[str] = None,
    top_k: int = 1,
    generate_gradcam: bool = False,
    confidence_threshold: float = 0.5,
    image_id: Optional[str] = None,
) -> PredictionResult:
    """
    Convenience wrapper: build a pipeline and run single-image inference.

    Parameters
    ----------
    source : str | bytes | Path
        Image file path or raw bytes.
    model_name : str | None
        Architecture to use. Defaults to settings.active_model.
    top_k : int
        Number of top predictions.
    generate_gradcam : bool
        Whether to produce a Grad-CAM heatmap.
    confidence_threshold : float
        Threshold for is_high_confidence flag.
    image_id : str | None
        Optional caller-supplied ID.

    Returns
    -------
    PredictionResult
    """
    cfg = InferenceConfig(
        model_name=(model_name or settings.active_model).lower(),
        top_k=top_k,
        generate_gradcam=generate_gradcam,
        confidence_threshold=confidence_threshold,
        class_names=settings.classes,
        image_size=settings.image_size,
    )
    return InferencePipeline(cfg).predict(source, image_id=image_id)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.inference.pipeline",
        description="Brain Tumour MRI inference CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "image",
        nargs="?",
        default=None,
        help="Path to a single MRI image (JPEG/PNG).",
    )
    p.add_argument(
        "--model", "-m",
        default=None,
        dest="model_name",
        choices=["cnn", "vgg16", "resnet50", "efficientnet"],
        help="Architecture to use for inference.",
    )
    p.add_argument(
        "--top-k", "-k",
        type=int,
        default=1,
        dest="top_k",
        help="Number of top-K predictions to show.",
    )
    p.add_argument(
        "--gradcam",
        action="store_true",
        default=False,
        help="Generate and save a Grad-CAM heatmap overlay.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        dest="confidence_threshold",
        help="Confidence threshold for high-confidence flag.",
    )
    p.add_argument(
        "--batch",
        default=None,
        dest="batch_dir",
        metavar="DIR",
        help="Run batch inference on all images in DIR.",
    )
    p.add_argument(
        "--zip",
        default=None,
        dest="zip_path",
        metavar="FILE",
        help="Run batch inference on all images in a ZIP archive.",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        dest="output_dir",
        help="Directory to write batch result JSON/CSV.",
    )
    return p


def _main() -> None:
    import json as _json

    parser = _build_arg_parser()
    args = parser.parse_args()

    model_name = args.model_name or settings.active_model

    cfg = InferenceConfig(
        model_name=model_name,
        top_k=args.top_k,
        generate_gradcam=args.gradcam,
        confidence_threshold=args.confidence_threshold,
        class_names=settings.classes,
        image_size=settings.image_size,
        output_dir=args.output_dir,
    )
    pipeline = InferencePipeline(cfg)

    # ── Batch directory ───────────────────────────────────────────────────────
    if args.batch_dir:
        batch_result = pipeline.predict_directory(args.batch_dir)
        print("\n" + "=" * 60)
        print("Batch inference complete")
        print("=" * 60)
        print(_json.dumps(batch_result.summary_dict(), indent=2, default=str))
        return

    # ── ZIP ───────────────────────────────────────────────────────────────────
    if args.zip_path:
        batch_result = pipeline.predict_zip(args.zip_path)
        print("\n" + "=" * 60)
        print("ZIP inference complete")
        print("=" * 60)
        print(_json.dumps(batch_result.summary_dict(), indent=2, default=str))
        return

    # ── Single image ──────────────────────────────────────────────────────────
    if args.image is None:
        parser.print_help()
        return

    result = pipeline.predict(args.image)
    print("\n" + "=" * 60)
    print("Prediction result")
    print("=" * 60)
    summary = {
        "image_id":         result.image_id,
        "predicted_class":  result.predicted_class,
        "confidence":       result.confidence,
        "is_high_confidence": result.is_high_confidence,
        "top_k": [t.to_dict() for t in result.top_k],
        "timing_ms":        result.timing_ms,
        "model":            result.metadata.model_name,
        "gradcam_path":     result.metadata.gradcam_path,
    }
    print(_json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    _main()
