"""
verify_imports.py — Verify all AI service dependencies import correctly.

Run from the ai-service/ directory (with the virtual environment activated):
    python scripts/verify_imports.py
"""

from __future__ import annotations

import importlib
import sys
from typing import List, Tuple

# (module_name, optional friendly_label)
REQUIRED_IMPORTS: List[Tuple[str, str]] = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("multipart", "python-multipart"),
    ("tensorflow", "TensorFlow"),
    ("keras", "Keras"),
    ("cv2", "OpenCV"),
    ("numpy", "NumPy"),
    ("pandas", "Pandas"),
    ("matplotlib", "Matplotlib"),
    ("sklearn", "Scikit-learn"),
    ("PIL", "Pillow"),
    ("tf_explain", "Grad-CAM (tf-explain)"),
    ("dotenv", "python-dotenv"),
    ("pydantic", "Pydantic"),
    ("pydantic_settings", "Pydantic Settings"),
    ("loguru", "Loguru"),
]

APP_IMPORTS: List[Tuple[str, str]] = [
    ("app.core.config", "config.py"),
    ("app.core.logging", "logging.py"),
    ("app.main", "app/main.py"),
    ("app.api.routes", "app/api/routes.py"),
    ("app.models.train", "train.py"),
    ("app.models.predict", "predict.py"),
    ("app.models.evaluate", "evaluate.py"),
    ("app.models.load_model", "load_model.py"),
    ("app.models.save_model", "save_model.py"),
]


def check_import(module_name: str, label: str) -> Tuple[bool, str]:
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, "__version__", "ok")
        return True, f"  OK  {label:<30} ({module_name}) — {version}"
    except ImportError as exc:
        return False, f"  FAIL {label:<30} ({module_name}) — {exc}"


def main() -> int:
    print("=" * 70)
    print("  AI Service — Dependency & Module Import Verification")
    print("=" * 70)
    print(f"Python: {sys.version}\n")

    all_ok = True

    print("── Third-party packages ──────────────────────────────────────────────")
    for module_name, label in REQUIRED_IMPORTS:
        ok, msg = check_import(module_name, label)
        print(msg)
        all_ok = all_ok and ok

    print("\n── Application modules ───────────────────────────────────────────────")
    for module_name, label in APP_IMPORTS:
        ok, msg = check_import(module_name, label)
        print(msg)
        all_ok = all_ok and ok

    print("\n" + "=" * 70)
    if all_ok:
        print("  All imports succeeded.")
        return 0
    else:
        print("  One or more imports FAILED. Run: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
