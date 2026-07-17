"""
app/inference/__init__.py — Public surface of the inference package.

Primary entry points:

    from app.inference import InferencePipeline, predict
    from app.inference import BatchInferenceRunner
    from app.inference import InferenceConfig, DEFAULT_INFERENCE_CONFIG
    from app.inference import PredictionResult, BatchPredictionResult
    from app.inference import get_model, reload_model, cache_stats
"""

from app.inference.cache import (
    ModelCache,
    cache_stats,
    clear_cache,
    evict_model,
    get_model,
    list_available_models,
    reload_model,
)
from app.inference.config import DEFAULT_INFERENCE_CONFIG, InferenceConfig
from app.inference.pipeline import InferencePipeline, predict
from app.inference.batch import BatchInferenceRunner
from app.inference.results import (
    BatchItemResult,
    BatchPredictionResult,
    PredictionMetadata,
    PredictionResult,
    TopKPrediction,
)

__all__ = [
    # Pipeline
    "InferencePipeline",
    "predict",
    # Batch
    "BatchInferenceRunner",
    # Config
    "InferenceConfig",
    "DEFAULT_INFERENCE_CONFIG",
    # Results
    "PredictionResult",
    "BatchPredictionResult",
    "BatchItemResult",
    "PredictionMetadata",
    "TopKPrediction",
    # Cache
    "ModelCache",
    "get_model",
    "reload_model",
    "evict_model",
    "clear_cache",
    "cache_stats",
    "list_available_models",
]
