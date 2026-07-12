"""Tests for FastAPI health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_200() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["status"] == "ok"
    assert body["service"] == "Brain Tumour Detection AI Service"
    assert "class_names" in body
    assert len(body["class_names"]) == 4


def test_predict_endpoint_returns_501() -> None:
    response = client.post(
        "/api/v1/predict",
        files={"image": ("test.png", b"fake", "image/png")},
    )
    assert response.status_code == 501


def test_train_endpoint_returns_501() -> None:
    response = client.post(
        "/api/v1/train",
        json={"model_name": "efficientnet", "epochs": 10, "batch_size": 16},
    )
    assert response.status_code == 501


def test_evaluate_endpoint_returns_501() -> None:
    response = client.post(
        "/api/v1/evaluate",
        json={"model_name": "efficientnet", "batch_size": 32},
    )
    assert response.status_code == 501
