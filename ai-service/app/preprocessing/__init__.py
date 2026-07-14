"""
app/preprocessing — Image preprocessing package.

Single import point for all preprocessing symbols.  Consumers only need:

    from app.preprocessing import preprocess_for_inference, PreprocessConfig
    from app.preprocessing import validate_image_quality, AugmentationConfig
"""

# ── Config ────────────────────────────────────────────────────────────────────
from app.preprocessing.config import (
    PreprocessConfig,
    DEFAULT_CONFIG,
    IMAGENET_MEAN,
    IMAGENET_STD,
)

# ── Transforms (pure stateless functions) ─────────────────────────────────────
from app.preprocessing.transforms import (
    load_image_bgr,
    encode_image_png,
    encode_image_base64,
    apply_median_filter,
    apply_gaussian_blur,
    apply_clahe,
    apply_histogram_equalisation,
    resize_image,
    pad_to_square,
    bgr_to_rgb,
    rgb_to_bgr,
    normalize_image,
    rescale_only,
    denormalize_image,
    apply_spatial_pipeline,
)

# ── Quality validation ────────────────────────────────────────────────────────
from app.preprocessing.quality import (
    QualityCheck,
    ImageQualityReport,
    validate_image_quality,
    validate_batch_quality,
)

# ── Augmentation ──────────────────────────────────────────────────────────────
from app.preprocessing.augmentation import (
    AugmentationConfig,
    DEFAULT_AUG_CONFIG,
    build_train_datagen,
    build_eval_datagen,
    build_data_generators_from_split,
    apply_augmentation,
)

# ── Pipeline entry-points (context-aware) ─────────────────────────────────────
from app.preprocessing.preprocess import (
    # New context-aware API
    preprocess_for_inference,
    preprocess_for_gradcam,
    preprocess_for_preview,
    build_generators,
    build_test_generator,
    # Backward-compatible shims
    preprocess_image,
    preprocess_image_for_gradcam,
    build_data_generators,
)

__all__ = [
    # config
    "PreprocessConfig",
    "DEFAULT_CONFIG",
    "IMAGENET_MEAN",
    "IMAGENET_STD",
    # transforms
    "load_image_bgr",
    "encode_image_png",
    "encode_image_base64",
    "apply_median_filter",
    "apply_gaussian_blur",
    "apply_clahe",
    "apply_histogram_equalisation",
    "resize_image",
    "pad_to_square",
    "bgr_to_rgb",
    "rgb_to_bgr",
    "normalize_image",
    "rescale_only",
    "denormalize_image",
    "apply_spatial_pipeline",
    # quality
    "QualityCheck",
    "ImageQualityReport",
    "validate_image_quality",
    "validate_batch_quality",
    # augmentation
    "AugmentationConfig",
    "DEFAULT_AUG_CONFIG",
    "build_train_datagen",
    "build_eval_datagen",
    "build_data_generators_from_split",
    "apply_augmentation",
    # pipeline
    "preprocess_for_inference",
    "preprocess_for_gradcam",
    "preprocess_for_preview",
    "build_generators",
    "build_test_generator",
    # shims
    "preprocess_image",
    "preprocess_image_for_gradcam",
    "build_data_generators",
]
