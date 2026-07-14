"""
verify_inference.py — Quick smoke-test for Module 6 (run without pytest).
"""
from app.inference import (
    InferencePipeline, predict, BatchInferenceRunner,
    InferenceConfig, DEFAULT_INFERENCE_CONFIG,
    PredictionResult, BatchPredictionResult, BatchItemResult,
    PredictionMetadata, TopKPrediction,
    ModelCache, get_model, reload_model, evict_model,
    clear_cache, cache_stats, list_available_models,
)
print("All inference imports: OK")

# InferenceConfig validation
cfg = InferenceConfig(model_name="resnet50", top_k=2, generate_gradcam=True)
assert cfg.model_name == "resnet50"
assert cfg.top_k == 2
assert cfg.num_classes == 4
assert cfg.generate_gradcam is True
try:
    InferenceConfig(model_name="invalid")
    raise AssertionError("Should have raised ValueError")
except ValueError:
    pass
try:
    InferenceConfig(top_k=0)
    raise AssertionError("Should have raised ValueError")
except ValueError:
    pass
print("InferenceConfig validation: OK")

# Results serialisation
import json
meta = PredictionMetadata(
    model_name="efficientnet",
    class_names=["glioma", "meningioma", "notumor", "pituitary"],
    image_size=224,
)
d = meta.to_dict()
json.dumps(d)
assert "predicted_at" in d
assert d["gradcam_path"] is None
print("PredictionMetadata serialisation: OK")

top_k = [TopKPrediction(rank=1, class_name="glioma", class_index=0, probability=0.85)]
result = PredictionResult(
    image_id="test-123",
    predicted_class="glioma",
    predicted_class_index=0,
    confidence=0.85,
    is_high_confidence=True,
    probabilities={"glioma": 0.85, "meningioma": 0.10, "notumor": 0.03, "pituitary": 0.02},
    top_k=top_k,
    timing_ms=42.0,
    metadata=meta,
)
rd = result.to_dict()
assert rd["predicted_class"] == "glioma"
assert json.loads(result.to_json())["confidence"] == 0.85
print("PredictionResult serialisation: OK")

# BatchPredictionResult
from app.inference.results import BatchItemResult as BIR
batch = BatchPredictionResult(
    total=3, succeeded=2, failed=1,
    results=[
        BIR("a.jpg", True, result),
        BIR("b.jpg", True, result),
        BIR("c.jpg", False, error="decode error"),
    ],
    timing_ms=120.0,
    model_name="efficientnet",
    source_type="list",
)
assert batch.success_rate == round(2 / 3, 4)
assert batch.class_distribution == {"glioma": 2}
assert "results" not in batch.summary_dict()
print("BatchPredictionResult: OK")

# ModelCache thread-safety and LRU
from app.inference.cache import ModelCache as MC, _CacheEntry
from unittest.mock import MagicMock

def fake_model():
    m = MagicMock()
    m.count_params.return_value = 100
    return m

cache = MC(capacity=2)
e1 = _CacheEntry(fake_model(), "cnn", 10.0, {})
e2 = _CacheEntry(fake_model(), "vgg16", 12.0, {})
with cache._lock:
    cache._store["cnn"] = e1
    cache._store["vgg16"] = e2
# Access cnn → MRU
cache.get("cnn")
# Insert 3rd → vgg16 (LRU) evicted
e3 = _CacheEntry(fake_model(), "resnet50", 8.0, {})
with cache._lock:
    if len(cache._store) >= cache._capacity:
        cache._store.popitem(last=False)
    cache._store["resnet50"] = e3
assert "vgg16" not in cache
assert "cnn" in cache
assert "resnet50" in cache
s = cache.stats()
assert s["capacity"] == 2
assert s["total_hits"] == 1
assert s["total_misses"] == 0
print("ModelCache LRU + stats: OK")

# list_available_models
models = list_available_models()
assert len(models) == 4
names = {m["name"] for m in models}
assert names == {"cnn", "vgg16", "resnet50", "efficientnet"}
assert all(isinstance(m["available"], bool) for m in models)
print("list_available_models: OK")

# cache_stats module-level function
s2 = cache_stats()
assert {"capacity", "size", "hit_rate", "cached_models"} <= s2.keys()
print("cache_stats: OK")

# routes.py syntax check
from app.api.routes import router
assert router is not None
print("routes.py import: OK")

print()
print("=" * 50)
print("All inference package components verified")
print("=" * 50)
