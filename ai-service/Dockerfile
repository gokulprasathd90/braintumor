# ─── ai-service/Dockerfile ────────────────────────────────────────────────────
#
# Multi-stage build for the Python / TensorFlow AI service.
#
# Stage 1 (builder) — installs all Python dependencies into a clean prefix so
#   only the compiled wheels are copied to the final image (no build tools).
#
# Stage 2 (runtime) — python:3.12-slim base, copies the installed packages
#   from the builder and the application source.
#
# CPU-only build (no CUDA).  TensorFlow 2.20 ships CPU kernels by default.
# To enable GPU support: change the base images to nvidia/cuda:12.x-cudnn9-runtime
# and set TF_CPP_MIN_LOG_LEVEL / CUDA_VISIBLE_DEVICES as needed.
#
# Build:
#   docker build -t brain-tumor-ai-service:latest ./ai-service
#
# Run (standalone):
#   docker run --rm -p 8000:8000 --env-file ai-service/.env brain-tumor-ai-service:latest

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Builder
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Build-time dependencies needed to compile native extensions
# (numpy, scipy, opencv headless, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements first to exploit layer caching —
# only re-runs pip install when requirements.txt changes.
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — Runtime
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Brain Tumour Detection — AI Service" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.description="FastAPI / TensorFlow inference service"

# Runtime OS libraries required by OpenCV headless and TensorFlow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source (excludes .venv, dataset, logs via .dockerignore)
COPY app/          ./app/
COPY pyproject.toml .

# Create runtime directories — mounted as volumes in docker-compose
RUN mkdir -p \
        saved_models \
        dataset/raw \
        dataset/processed \
        gradcam_output \
        logs

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

# ── Environment defaults (all overridden by docker-compose / .env) ────────────
ENV AI_SERVICE_HOST=0.0.0.0 \
    AI_SERVICE_PORT=8000 \
    AI_SERVICE_ENV=production \
    AI_SERVICE_DEBUG=false \
    LOG_LEVEL=INFO \
    ACTIVE_MODEL=efficientnet \
    IMAGE_SIZE=224 \
    IMAGE_CHANNELS=3 \
    CLASS_NAMES=glioma,meningioma,notumor,pituitary \
    # Suppress TF verbose startup messages
    TF_CPP_MIN_LOG_LEVEL=2 \
    TF_ENABLE_ONEDNN_OPTS=0

EXPOSE 8000

# Graceful shutdown: uvicorn responds to SIGTERM
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" \
    || exit 1

# 2 workers for production; override with --workers flag or UVICORN_WORKERS env
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--no-access-log"]
