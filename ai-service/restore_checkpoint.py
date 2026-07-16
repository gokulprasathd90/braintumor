"""
restore_checkpoint.py -- Rebuild EfficientNetB3, load Phase-1 checkpoint,
save to efficientnet.keras so inference works immediately.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import json, numpy as np
from pathlib import Path
from datetime import datetime, timezone

import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.applications import EfficientNetB3

IMG_SIZE   = 224
CKPT_PATH  = Path("saved_models/efficientnet/checkpoints/best_phase1.weights.h5")
MODEL_PATH = Path("saved_models/efficientnet/efficientnet.keras")
INFO_PATH  = Path("saved_models/efficientnet/model_info.json")
CLASSES    = ["glioma", "meningioma", "notumor", "pituitary"]

print("=" * 60)
print("Restoring from checkpoint:", str(CKPT_PATH))
print("=" * 60)

backbone = EfficientNetB3(
    include_top=False, weights="imagenet",
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
)
backbone.trainable = True

inp  = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="input_image")
x    = backbone(inp, training=False)
x    = layers.GlobalAveragePooling2D(name="gap")(x)
x    = layers.BatchNormalization(name="bn_head")(x)
x    = layers.Dense(256, activation="relu", name="fc1")(x)
x    = layers.Dropout(0.4, name="dropout_head")(x)
out  = layers.Dense(4, activation="softmax", name="predictions")(x)
model = models.Model(inp, out, name="efficientnet")

model.compile(
    optimizer=optimizers.Adam(1e-3),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

model.load_weights(str(CKPT_PATH))
print(f"Checkpoint loaded -- {model.count_params():,} params")

# Sanity: predictions must NOT all converge to ~25%
dummy = np.random.rand(4, IMG_SIZE, IMG_SIZE, 3).astype(np.float32)
preds = model.predict(dummy, verbose=0)
print("\n[SANITY] 4 random images, predictions:")
for i, p in enumerate(preds):
    top = CLASSES[int(np.argmax(p))]
    vals = " | ".join(f"{c}:{v:.3f}" for c, v in zip(CLASSES, p))
    print(f"  img{i}: {top} ({max(p)*100:.1f}%)  [{vals}]")

max_conf = float(np.max(preds))
assert max_conf > 0.35, f"Predictions still uniform -- checkpoint not loaded? max={max_conf}"
print("\nSanity check PASSED -- predictions are non-uniform")

model.save(str(MODEL_PATH))
print(f"\nModel saved -> {MODEL_PATH}")

info = {
    "model_name":    "efficientnet",
    "save_format":   "keras",
    "input_shape":   [IMG_SIZE, IMG_SIZE, 3],
    "num_classes":   4,
    "class_names":   CLASSES,
    "class_indices": {"glioma": 0, "meningioma": 1, "notumor": 2, "pituitary": 3},
    "total_params":  model.count_params(),
    "saved_at":      datetime.now(timezone.utc).isoformat(),
    "model_path":    str(MODEL_PATH),
    "h5_path":       str(MODEL_PATH),
    "bootstrap":     False,
    "preprocessing": "rescale_only_div255",
    "training_phase": "phase1_checkpoint_epoch5",
    "val_accuracy":  0.4809,
    "note": (
        "Phase-1 checkpoint (5 epochs, frozen backbone). "
        "Preprocessing: /255 rescale only -- no ImageNet z-score. "
        "Phase-2 fine-tuning will improve accuracy further."
    ),
}
INFO_PATH.write_text(json.dumps(info, indent=2))
print(f"model_info.json updated -> {INFO_PATH}")
print("=" * 60)
print("DONE -- AI service can run real inference now.")
print("=" * 60)
