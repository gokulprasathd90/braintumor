"""
routes.py — FastAPI route definitions for the AI service.

Endpoints
---------
GET  /health        Liveness probe — returns server status and config snapshot.
POST /predict       Accept an MRI image, run inference, return prediction.
POST /train         Trigger model training (async job placeholder).
POST /evaluate      Evaluate a trained model against the test split.

All ML endpoints return 501 Not Implemented until the model layer is built.
The request / response schemas are defined here using Pydantic models so the
Node.js backend and frontend can rely on a stable contract.
"""

from __future__ import annotations

import platform
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter()


# ─── Shared response / request schemas ───────────────────────────────────────

class HealthResponse(BaseModel):
    success: bool
    status: str
    service: str
    version: str
    timestamp: str
    environment: str
    active_model: str
    class_names: List[str]
    image_size: int
    python_version: str


class PredictionResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class TrainRequest(BaseModel):
    model_name: str = Field(
        default="efficientnet",
        description="Architecture to train: cnn | vgg16 | resnet50 | efficientnet",
    )
    epochs: int        = Field(default=30,    ge=1,   le=500)
    batch_size: int    = Field(default=32,    ge=1,   le=256)
    learning_rate: float = Field(default=1e-4, gt=0.0, lt=1.0)


class TrainResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class EvaluateRequest(BaseModel):
    model_name: Optional[str] = Field(
        default=None,
        description="Architecture to evaluate. Defaults to settings.active_model.",
    )
    batch_size: int = Field(default=32, ge=1, le=256)


class EvaluateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ─── GET /health ─────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    tags=["System"],
)
def health_check() -> HealthResponse:
    """
    Returns 200 with server metadata.

    Used by the Node.js backend and Docker health-check to confirm the
    AI service is reachable and correctly configured.
    """
    return HealthResponse(
        success=True,
        status="ok",
        service="Brain Tumour Detection AI Service",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.ai_service_env,
        active_model=settings.active_model,
        class_names=settings.classes,
        image_size=settings.image_size,
        python_version=platform.python_version(),
    )


# ─── POST /predict ────────────────────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run inference on an MRI image",
    tags=["Inference"],
)
async def predict_endpoint(
    image: UploadFile = File(..., description="MRI scan — JPEG or PNG"),
    model_name: Optional[str] = Form(
        default=None,
        description="Override the active model (cnn | vgg16 | resnet50 | efficientnet)",
    ),
) -> PredictionResponse:
    """
    Accept an MRI image upload and return a tumour classification result.

    **Request** — multipart/form-data:
    - `image`      : JPEG or PNG file field
    - `model_name` : optional string form field to override the active model

    **Response**:
    ```json
    {
      "success": true,
      "data": {
        "class": "glioma",
        "confidence": 0.94,
        "probabilities": {"glioma": 0.94, "meningioma": 0.03, ...},
        "gradcam_url": "/processed/gradcam/<image_id>.png"
      }
    }
    ```

    Returns **501** until the model implementation is complete.
    """
    # Validate file type
    if image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{image.content_type}'. "
                   "Only image/jpeg and image/png are accepted.",
        )

    # TODO: read image bytes, preprocess, run predict(), return result
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Prediction endpoint is not yet implemented. "
               "The deep learning model will be added in the next phase.",
    )


# ─── POST /train ──────────────────────────────────────────────────────────────

@router.post(
    "/train",
    response_model=TrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger model training",
    tags=["Training"],
)
async def train_endpoint(body: TrainRequest) -> TrainResponse:
    """
    Start a model training job.

    Accepts hyperparameter configuration and queues a training run.
    Will return **202 Accepted** immediately with a job ID once the
    background task system is implemented.

    Returns **501** until the training implementation is complete.
    """
    # TODO: validate dataset directory exists, enqueue BackgroundTask
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Training endpoint is not yet implemented. "
               "Deep learning training will be added in the next phase.",
    )


# ─── POST /evaluate ───────────────────────────────────────────────────────────

@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a trained model",
    tags=["Training"],
)
async def evaluate_endpoint(body: EvaluateRequest) -> EvaluateResponse:
    """
    Run the evaluation loop on the held-out test split and return metrics.

    **Response** (once implemented):
    ```json
    {
      "success": true,
      "data": {
        "accuracy": 0.97,
        "precision": 0.97,
        "recall": 0.96,
        "f1": 0.96,
        "auc_roc": 0.99,
        "confusion_matrix": [[...], ...]
      }
    }
    ```

    Returns **501** until the evaluation implementation is complete.
    """
    # TODO: call evaluate_model() and return structured metrics
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Evaluation endpoint is not yet implemented. "
               "Metrics computation will be added in the next phase.",
    )
