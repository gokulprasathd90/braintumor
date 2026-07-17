"""
train_finetune.py — Phase-2 fine-tuning with memory-safe settings.

Loads Phase-1 checkpoint, unfreezes top-30 backbone layers, trains for
15 more epochs with LR=1e-5 and batch=8 (avoids MKL OOM on CPU).

Run from ai-service/:
    python train_finetune.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["TF_CPP_MIN_LOG_LEVEL"]    = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"]   = "0"   # disable MKL oneDNN → avoids OOM
os.environ["OMP_NUM_THREADS"]         = "4"
os.environ["TF_NUM_INTRAOP_THREADS"]  = "4"
os.environ["TF_NUM_INTEROP_THREADS"]  = "2"

import json, numpy as np
from pathlib import Path
from datetime import datetime, timezone

import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, optimizers
from tensorflow.keras.applications import EfficientNetB3
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import confusion_matrix, classification_report

IMG_SIZE   = 224
BATCH      = 8          # small batch → avoids MKL memory error
EPOCHS_P2  = 15
LR_P2      = 1e-5

SPLIT_DIR  = Path("dataset/processed")
MODEL_DIR  = Path("saved_models/efficientnet")
CKPT_P1    = MODEL_DIR / "checkpoints" / "best_phase1.weights.h5"
CKPT_P2    = MODEL_DIR / "checkpoints" / "best_phase2.weights.h5"
MODEL_PATH = MODEL_DIR / "efficientnet.keras"
INFO_PATH  = MODEL_DIR / "model_info.json"
CLASSES    = ["glioma", "meningioma", "notumor", "pituitary"]

print("\n" + "="*60)
print(f"  Phase-2 Fine-tuning  |  batch={BATCH}  epochs={EPOCHS_P2}")
print("="*60)

# ── Limit TF memory growth ────────────────────────────────────────────────────
gpus = tf.config.list_physical_devices("GPU")
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    print(f"  GPU: {[g.name for g in gpus]}")
else:
    print("  Running on CPU")

# ── Data generators ───────────────────────────────────────────────────────────
train_gen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    width_shift_range=0.15,
    height_shift_range=0.15,
    shear_range=0.1,
    zoom_range=0.15,
    horizontal_flip=True,
    fill_mode="nearest",
).flow_from_directory(
    str(SPLIT_DIR / "train"),
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH,
    class_mode="categorical",
    shuffle=True, seed=42,
)

val_gen = ImageDataGenerator(rescale=1./255).flow_from_directory(
    str(SPLIT_DIR / "val"),
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH,
    class_mode="categorical",
    shuffle=False,
)

test_gen = ImageDataGenerator(rescale=1./255).flow_from_directory(
    str(SPLIT_DIR / "test"),
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH,
    class_mode="categorical",
    shuffle=False,
)

print(f"\n[DATA] class_indices: {train_gen.class_indices}")
print(f"[DATA] train={train_gen.samples}  val={val_gen.samples}  test={test_gen.samples}")

# Confirm class order
actual = train_gen.class_indices
assert actual == {"glioma": 0, "meningioma": 1, "notumor": 2, "pituitary": 3}, \
    f"Class order mismatch: {actual}"
print("[DATA] Class order verified: glioma=0 meningioma=1 notumor=2 pituitary=3")

# ── Class weights ─────────────────────────────────────────────────────────────
counts = {c: len(list((SPLIT_DIR / "train" / c).glob("*.*"))) for c in CLASSES}
total  = sum(counts.values())
class_weight = {actual[c]: total / (4 * counts[c]) for c in CLASSES}
print(f"[DATA] class_weights: { {k: round(v, 3) for k, v in class_weight.items()} }")

# ── Rebuild model (same arch as Phase 1) ─────────────────────────────────────
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

# Load Phase-1 weights
model.load_weights(str(CKPT_P1))
print(f"\n[CKPT] Loaded Phase-1 weights from {CKPT_P1}")

# Freeze all but top-30 backbone layers; keep BatchNorm frozen
for layer in backbone.layers[:-30]:
    layer.trainable = False
for layer in backbone.layers:
    if isinstance(layer, layers.BatchNormalization):
        layer.trainable = False

trainable_count = sum(1 for l in model.layers if l.trainable)
print(f"[MODEL] Trainable layers: {trainable_count}")

model.compile(
    optimizer=optimizers.Adam(LR_P2),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

# ── Phase-2 callbacks ─────────────────────────────────────────────────────────
CKPT_P2.parent.mkdir(parents=True, exist_ok=True)
cbs = [
    callbacks.ModelCheckpoint(
        str(CKPT_P2),
        monitor="val_accuracy", save_best_only=True,
        save_weights_only=True, mode="max", verbose=1,
    ),
    callbacks.EarlyStopping(
        monitor="val_accuracy", patience=6,
        restore_best_weights=True, verbose=1,
    ),
    callbacks.ReduceLROnPlateau(
        monitor="val_loss", factor=0.5, patience=3,
        min_lr=1e-7, verbose=1,
    ),
]

# ── Train ─────────────────────────────────────────────────────────────────────
print(f"\n[PHASE 2] Fine-tuning for up to {EPOCHS_P2} epochs …")
h = model.fit(
    train_gen, epochs=EPOCHS_P2,
    validation_data=val_gen,
    class_weight=class_weight,
    callbacks=cbs,
)

best_val_acc = max(h.history["val_accuracy"])
print(f"\n[PHASE 2] Best val_accuracy: {best_val_acc:.4f}")

# ── Evaluate on test set ──────────────────────────────────────────────────────
print(f"\n[EVAL] Test-set evaluation …")
test_gen.reset()
y_pred_probs = model.predict(test_gen, verbose=1)
y_pred = np.argmax(y_pred_probs, axis=1)
y_true = test_gen.classes
idx_to_cls = {v: k for k, v in train_gen.class_indices.items()}

cm = confusion_matrix(y_true, y_pred)
print("\n[CONFUSION MATRIX]  rows=true  cols=pred")
header = "           " + "  ".join(f"{c:>11}" for c in CLASSES)
print(header)
for i, row in enumerate(cm):
    print(f"  {CLASSES[i]:>9} " + "  ".join(f"{v:>11}" for v in row))

report = classification_report(
    [idx_to_cls[i] for i in y_true],
    [idx_to_cls[i] for i in y_pred],
    target_names=CLASSES, digits=4,
)
print("\n[CLASSIFICATION REPORT]")
print(report)

test_loss, test_acc = model.evaluate(test_gen, verbose=0)
print(f"[TEST] accuracy={test_acc:.4f}  loss={test_loss:.4f}")

# ── Save final model ──────────────────────────────────────────────────────────
MODEL_DIR.mkdir(parents=True, exist_ok=True)
model.save(str(MODEL_PATH))
print(f"\n[SAVE] Model → {MODEL_PATH}")

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
    "training_phase": "phase2_finetuned",
    "val_accuracy":  float(best_val_acc),
    "test_accuracy": float(test_acc),
    "note": (
        "Full fine-tuned model. Preprocessing: /255 rescale only. "
        "Phase-2: top-30 backbone layers unfrozen, oneDNN disabled."
    ),
}
INFO_PATH.write_text(json.dumps(info, indent=2))
print(f"[SAVE] model_info.json → {INFO_PATH}")
print(f"\n{'='*60}")
print(f"  COMPLETE — test_accuracy={test_acc:.4f}")
print(f"  Class order: {CLASSES}")
print(f"{'='*60}")
