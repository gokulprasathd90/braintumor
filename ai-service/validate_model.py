"""
validate_model.py -- Full validation report on the current saved model.

Runs inference on every image in dataset/processed/test/ using the same
preprocessing pipeline as the live server (rescale /255, CLAHE, denoise).
Produces:
  - Per-sample predictions with confidence
  - Confusion matrix
  - Per-class accuracy, precision, recall, F1
  - Overall accuracy
  - Sample predictions for each class

Run from ai-service/:
    python -X utf8 validate_model.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
from pathlib import Path

SPLIT_DIR  = Path("dataset/processed/test")
MODEL_PATH = Path("saved_models/efficientnet/efficientnet.keras")
CLASSES    = ["glioma", "meningioma", "notumor", "pituitary"]

# ── Load model ────────────────────────────────────────────────────────────────
import tensorflow as tf
from tensorflow.keras.models import load_model
print("Loading model from:", MODEL_PATH)
model = load_model(str(MODEL_PATH))
print(f"  params : {model.count_params():,}")
print(f"  input  : {model.input_shape}")
print(f"  output : {model.output_shape}")

# ── Run inference using the SAME pipeline as the live server ──────────────────
from app.preprocessing.preprocess import preprocess_for_inference
from app.preprocessing.config import DEFAULT_CONFIG

print(f"\nPreprocessing config:")
print(f"  normalise    = {DEFAULT_CONFIG.normalise}  (False = /255 rescale only)")
print(f"  apply_clahe  = {DEFAULT_CONFIG.apply_clahe}")
print(f"  apply_denoise= {DEFAULT_CONFIG.apply_denoise}")
print(f"  image_size   = {DEFAULT_CONFIG.image_size}")

y_true, y_pred, y_conf = [], [], []
samples_shown = {c: 0 for c in CLASSES}
MAX_SHOW = 3   # show up to 3 samples per class

print(f"\n{'='*72}")
print(f"  SAMPLE PREDICTIONS  (first {MAX_SHOW} per class)")
print(f"{'='*72}")
print(f"  {'Image':<40} {'True':<12} {'Pred':<12} {'Conf':>6}  {'OK'}")
print(f"  {'-'*40} {'-'*12} {'-'*12} {'-'*6}  {'-'*3}")

for cls_idx, cls_name in enumerate(CLASSES):
    cls_dir = SPLIT_DIR / cls_name
    if not cls_dir.exists():
        print(f"  [WARN] missing test dir: {cls_dir}")
        continue
    imgs = sorted(cls_dir.glob("*.jpg")) + sorted(cls_dir.glob("*.jpeg")) + sorted(cls_dir.glob("*.png"))
    for img_path in imgs:
        tensor = preprocess_for_inference(str(img_path), expand_dims=True)
        probs  = model.predict(tensor, verbose=0)[0]
        pred_idx = int(np.argmax(probs))
        conf     = float(probs[pred_idx])
        y_true.append(cls_idx)
        y_pred.append(pred_idx)
        y_conf.append(conf)
        if samples_shown[cls_name] < MAX_SHOW:
            ok = "OK" if pred_idx == cls_idx else "WRONG"
            print(f"  {img_path.name:<40} {cls_name:<12} {CLASSES[pred_idx]:<12} {conf:>5.1%}  {ok}")
            samples_shown[cls_name] += 1

y_true = np.array(y_true)
y_pred = np.array(y_pred)
y_conf = np.array(y_conf)
n = len(y_true)

# ── Confusion matrix ──────────────────────────────────────────────────────────
from sklearn.metrics import confusion_matrix, classification_report

cm = confusion_matrix(y_true, y_pred)
print(f"\n{'='*72}")
print(f"  CONFUSION MATRIX   (rows = true class, cols = predicted class)")
print(f"{'='*72}")
col_w = 13
header = " " * 14 + "".join(f"{c:>{col_w}}" for c in CLASSES)
print(header)
print(" " * 14 + "-" * (col_w * len(CLASSES)))
for i, row in enumerate(cm):
    row_str = f"  {CLASSES[i]:>11} |" + "".join(f"{v:>{col_w}}" for v in row)
    print(row_str)

# ── Per-class metrics ─────────────────────────────────────────────────────────
print(f"\n{'='*72}")
print(f"  PER-CLASS ACCURACY  (correctly classified / total in class)")
print(f"{'='*72}")
print(f"  {'Class':<14} {'Correct':>8} {'Total':>7} {'Accuracy':>10} {'Precision':>10} {'Recall':>8} {'F1':>8}")
print(f"  {'-'*14} {'-'*8} {'-'*7} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")

for i, cls_name in enumerate(CLASSES):
    mask    = y_true == i
    correct = int(np.sum(y_pred[mask] == i))
    total   = int(np.sum(mask))
    acc     = correct / total if total > 0 else 0.0
    # Precision: TP / (TP + FP)
    tp = correct
    fp = int(np.sum((y_pred == i) & (y_true != i)))
    fn = total - correct
    prec   = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1     = 2 * prec * recall / (prec + recall) if (prec + recall) > 0 else 0.0
    print(f"  {cls_name:<14} {correct:>8} {total:>7} {acc:>9.2%}  {prec:>9.2%} {recall:>7.2%} {f1:>7.2%}")

overall_acc = float(np.mean(y_true == y_pred))
avg_conf    = float(np.mean(y_conf))
print(f"\n  Overall accuracy  : {overall_acc:.4f}  ({overall_acc:.2%})")
print(f"  Avg confidence    : {avg_conf:.4f}  ({avg_conf:.2%})")
print(f"  Test samples      : {n}")

# ── sklearn classification report ─────────────────────────────────────────────
y_true_names = [CLASSES[i] for i in y_true]
y_pred_names = [CLASSES[i] for i in y_pred]
report = classification_report(y_true_names, y_pred_names,
                                target_names=CLASSES, digits=4)
print(f"\n{'='*72}")
print(f"  SKLEARN CLASSIFICATION REPORT")
print(f"{'='*72}")
print(report)

# ── Per-class confidence histogram ───────────────────────────────────────────
print(f"{'='*72}")
print(f"  AVERAGE CONFIDENCE PER TRUE CLASS")
print(f"{'='*72}")
for i, cls_name in enumerate(CLASSES):
    mask = y_true == i
    if mask.sum() == 0:
        continue
    class_confs = y_conf[mask]
    correct_mask = y_pred[mask] == i
    print(f"  {cls_name:<14}  mean_conf={np.mean(class_confs):.3f}  "
          f"correct_conf={np.mean(class_confs[correct_mask]):.3f if correct_mask.sum()>0 else 0:.3f}  "
          f"wrong_conf={np.mean(class_confs[~correct_mask]):.3f if (~correct_mask).sum()>0 else 0:.3f}")

print(f"\n{'='*72}")
print(f"  VALIDATION COMPLETE")
print(f"  Model   : {MODEL_PATH}")
print(f"  Phase   : phase1_checkpoint_epoch5  val_acc_during_train=0.4809")
print(f"  Test acc: {overall_acc:.4f}")
print(f"  NOTE: Phase-2 fine-tuning still running -- accuracy will improve.")
print(f"{'='*72}")
