# ─────────────────────────────────────────────────────────────────────────────
# Brain Tumour Detection — AI Service
# Makefile targets
# ─────────────────────────────────────────────────────────────────────────────
#
# Usage
# -----
#   make train                              # EfficientNetB3, 30 epochs (defaults)
#   make train ARCH=resnet50 EPOCHS=20      # ResNet-50, 20 epochs
#   make train ARCH=cnn EPOCHS=50 BS=16     # Lightweight CNN, 50 epochs, batch 16
#   make train ARCH=vgg16 LR=5e-5 FT=false # VGG-16, no fine-tuning
#
#   make evaluate                           # evaluate active model on test split
#   make evaluate ARCH=resnet50
#
#   make prepare-dataset                    # validate + split raw dataset
#   make run                                # start dev server (uvicorn --reload)
#   make test                               # run pytest suite
#   make lint                               # ruff + mypy
#   make format                             # ruff format (auto-fix)
#   make clean                              # remove __pycache__, *.pyc, .pytest_cache
#
# ─────────────────────────────────────────────────────────────────────────────

# ── Configurable variables (override on the command line) ────────────────────
ARCH     ?= efficientnet      # cnn | vgg16 | resnet50 | efficientnet
EPOCHS   ?= 30
BS       ?= 32
LR       ?= 1e-4
FT       ?= true              # true | false  (Phase-2 fine-tuning)
FT_L     ?= 20                # fine-tune layers
FT_E     ?= 10                # fine-tune epochs
SEED     ?= 42
DATA_DIR ?=                   # leave empty to use settings.dataset_processed_dir

# ── Inference variables ───────────────────────────────────────────────────────
IMAGE    ?=                   # path to a single MRI image (required for make predict)
DIR      ?=                   # directory for make predict-batch
ZIP      ?=                   # ZIP archive for make predict-zip
TOP_K    ?= 1                 # top-K predictions
GRADCAM  ?=                   # set to --gradcam to enable heatmap
OUT_DIR  ?=                   # output directory for batch results

# ── Python interpreter ────────────────────────────────────────────────────────
PYTHON   ?= python

# ── Derived: optional --dataset-dir flag ─────────────────────────────────────
ifdef DATA_DIR
  _DATA_FLAG = --dataset-dir $(DATA_DIR)
else
  _DATA_FLAG =
endif

# ── Fine-tune flag ────────────────────────────────────────────────────────────
ifeq ($(FT),false)
  _FT_FLAG = --no-fine-tune
else
  _FT_FLAG =
endif

.PHONY: train evaluate prepare-dataset run test lint format clean \
        predict predict-batch predict-zip models reload-model help

# ── Default target ────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "Brain Tumour AI Service — available targets"
	@echo "─────────────────────────────────────────────────────────────────────"
	@echo "  make train                     Train with default settings (EfficientNetB3)"
	@echo "  make train ARCH=resnet50       Override architecture"
	@echo "  make train EPOCHS=20 BS=16     Override epochs and batch size"
	@echo "  make train LR=5e-5 FT=false    Override LR and disable fine-tuning"
	@echo "  make evaluate                  Evaluate active model on test split"
	@echo "  make evaluate ARCH=resnet50    Evaluate a specific architecture"
	@echo "  make prepare-dataset           Prepare (validate + split) raw dataset"
	@echo "  make run                       Start development server (uvicorn --reload)"
	@echo "  make test                      Run pytest test suite"
	@echo "  make lint                      Run ruff linter + mypy type checks"
	@echo "  make format                    Auto-format code with ruff"
	@echo "  make clean                     Remove build artefacts and caches"
	@echo "  ── Inference ──────────────────────────────────────────────────────"
	@echo "  make predict IMAGE=scan.jpg        Single-image prediction"
	@echo "  make predict IMAGE=scan.jpg GRADCAM=--gradcam  With Grad-CAM"
	@echo "  make predict IMAGE=scan.jpg TOP_K=3            Top-3 predictions"
	@echo "  make predict-batch DIR=dataset/test            Batch from directory"
	@echo "  make predict-zip ZIP=images.zip                Batch from ZIP"
	@echo "  make models                        List all models + cache status"
	@echo "  make reload-model                  Hot-reload the active model"
	@echo "  make reload-model ARCH=resnet50    Hot-reload a specific model"
	@echo "─────────────────────────────────────────────────────────────────────"
	@echo ""

# ── Training ──────────────────────────────────────────────────────────────────
# Calls the CLI entry point:  python -m training.trainer [flags]
#
# Example:  make train ARCH=resnet50 EPOCHS=20 BS=16 LR=1e-4
train:
	@echo "Starting training | arch=$(ARCH) epochs=$(EPOCHS) batch=$(BS) lr=$(LR)"
	$(PYTHON) -m training.trainer \
		--architecture $(ARCH) \
		--epochs       $(EPOCHS) \
		--batch-size   $(BS) \
		--learning-rate $(LR) \
		--fine-tune-layers $(FT_L) \
		--fine-tune-epochs $(FT_E) \
		--seed         $(SEED) \
		$(_FT_FLAG) \
		$(_DATA_FLAG)

# ── Evaluation ────────────────────────────────────────────────────────────────
evaluate:
	@echo "Evaluating model | arch=$(ARCH)"
	$(PYTHON) -c "\
import json; \
from app.models.evaluate import evaluate_model; \
m = evaluate_model('$(ARCH)'); \
print(json.dumps({k:v for k,v in m.items() if k not in ('confusion_matrix','per_class','model_info')}, indent=2)); \
print('confusion_matrix:', m.get('confusion_matrix')); \
"

# ── Dataset preparation ───────────────────────────────────────────────────────
prepare-dataset:
	@echo "Preparing dataset …"
	$(PYTHON) scripts/prepare_dataset.py

# ── Dev server ────────────────────────────────────────────────────────────────
# Run this manually in your terminal — it is a long-running process.
run:
	@echo ""
	@echo "Run this in your terminal:"
	@echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
	@echo ""

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v --tb=short

# ── Lint / Format ─────────────────────────────────────────────────────────────
lint:
	$(PYTHON) -m ruff check app/ training/ tests/
	$(PYTHON) -m mypy app/ training/ --ignore-missing-imports --no-error-summary

format:
	$(PYTHON) -m ruff format app/ training/ tests/
	$(PYTHON) -m ruff check app/ training/ tests/ --fix

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	@echo "Cleaning build artefacts …"
	find . -type d -name "__pycache__"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "Clean complete."

# ─────────────────────────────────────────────────────────────────────────────
# Inference targets
# ─────────────────────────────────────────────────────────────────────────────

# ── Derived: optional --output-dir flag ───────────────────────────────────────
ifdef OUT_DIR
  _OUT_FLAG = --output-dir $(OUT_DIR)
else
  _OUT_FLAG =
endif

# ── make predict IMAGE=path/to/scan.jpg ───────────────────────────────────────
# Optional: TOP_K=3  GRADCAM=--gradcam  ARCH=resnet50
predict:
ifndef IMAGE
	$(error IMAGE is required. Usage: make predict IMAGE=path/to/scan.jpg)
endif
	@echo "Running single-image inference | image=$(IMAGE) model=$(ARCH) top_k=$(TOP_K)"
	$(PYTHON) -m app.inference.pipeline $(IMAGE) \
		--model $(ARCH) \
		--top-k $(TOP_K) \
		$(GRADCAM)

# ── make predict-batch DIR=dataset/test ───────────────────────────────────────
# Optional: ARCH=resnet50  TOP_K=3  OUT_DIR=output/  GRADCAM=--gradcam
predict-batch:
ifndef DIR
	$(error DIR is required. Usage: make predict-batch DIR=path/to/directory)
endif
	@echo "Running batch inference | dir=$(DIR) model=$(ARCH) workers=4"
	$(PYTHON) -m app.inference.pipeline \
		--batch $(DIR) \
		--model $(ARCH) \
		--top-k $(TOP_K) \
		$(GRADCAM) \
		$(_OUT_FLAG)

# ── make predict-zip ZIP=images.zip ───────────────────────────────────────────
# Optional: ARCH=resnet50  TOP_K=3  OUT_DIR=output/  GRADCAM=--gradcam
predict-zip:
ifndef ZIP
	$(error ZIP is required. Usage: make predict-zip ZIP=path/to/archive.zip)
endif
	@echo "Running ZIP inference | zip=$(ZIP) model=$(ARCH)"
	$(PYTHON) -m app.inference.pipeline \
		--zip $(ZIP) \
		--model $(ARCH) \
		--top-k $(TOP_K) \
		$(GRADCAM) \
		$(_OUT_FLAG)

# ── make models ───────────────────────────────────────────────────────────────
# Lists all architectures with their availability and cache status
models:
	@echo "Listing models …"
	$(PYTHON) -c "\
import json; \
from app.inference.cache import list_available_models, cache_stats; \
models = list_available_models(); \
stats  = cache_stats(); \
print(json.dumps({'cache_stats': stats, 'models': models}, indent=2)); \
"

# ── make reload-model [ARCH=efficientnet] ─────────────────────────────────────
# Hot-reloads the model by evicting it from the process cache.
# NOTE: This applies to the current Python process only — the running server
#       has a separate process. Use POST /api/v1/models/reload to hot-reload
#       the live server without a restart.
reload-model:
	@echo "Reloading model '$(ARCH)' from disk …"
	$(PYTHON) -c "\
from app.inference.cache import reload_model; \
import json; \
m = reload_model('$(ARCH)'); \
print(json.dumps({'status': 'reloaded', 'model': '$(ARCH)', 'params': m.count_params()}, indent=2)); \
"
