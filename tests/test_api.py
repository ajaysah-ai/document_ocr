"""API tests with a fake OCR service - no real identity images needed."""
from __future__ import annotations

import io
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api import routes
from backend.main import app


class _FakeOCRService:
    """Deterministic stand-in for PaddleOCR."""

    ready = True
    error = None

    def initialize(self) -> None:
        return None

    def run(self, image_path):  # noqa: ARG002
        texts = ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER",
                 "ABCDE1234F", "NAME: AJAY SAH", "01/01/2000"]
        items = []
        for i, text in enumerate(texts):
            bbox = [10, 10 + i * 40, 310, 40 + i * 40]
            items.append({
                "text": text,
                "confidence": 0.96,
                "bbox": bbox,
                "polygon": [[bbox[0], bbox[1]], [bbox[2], bbox[1]],
                            [bbox[2], bbox[3]], [bbox[0], bbox[3]]],
            })
        return items, {}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(routes, "_service", _FakeOCRService())
    with TestClient(app) as test_client:
        yield test_client


def _png_bytes() -> bytes:
    image = np.full((600, 800, 3), 255, np.uint8)
    cv2.putText(image, "SYNTHETIC DOC", (40, 300), cv2.FONT_HERSHEY_SIMPLEX,
                1.4, (0, 0, 0), 3)
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ocr"] in {"ready", "unavailable"}


def test_ocr_full_flow(client):
    response = client.post(
        "/api/ocr",
        files={"file": ("pan_card.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["document_type"] == "PAN"
    assert body["structured_data"]["pan_number"]["value"] == "ABCDE1234F"
    assert len(body["regions"]) == 5
    assert body["regions"][0]["bbox"] == [10, 10, 310, 50]
    assert body["quality"]["width"] == 800
    assert body["processing_time_ms"] >= 0
    # JSON must be pure native types (NumPy converted upstream).
    json.dumps(body)


def test_unsupported_extension_rejected(client):
    response = client.post(
        "/api/ocr",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


def test_corrupted_image_rejected(client):
    response = client.post(
        "/api/ocr",
        files={"file": ("fake.png", io.BytesIO(b"not an image"), "image/png")},
    )
    assert response.status_code == 400


def test_oversized_file_rejected(client, monkeypatch):
    monkeypatch.setattr(routes.settings, "max_file_size_mb", 0)
    response = client.post(
        "/api/ocr",
        files={"file": ("big.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert response.status_code == 413


def test_temp_files_cleaned_up(client):
    from backend.config import settings

    before = set(settings.upload_dir.iterdir())
    client.post("/api/ocr",
                files={"file": ("doc.png", io.BytesIO(_png_bytes()), "image/png")})
    after = set(settings.upload_dir.iterdir())
    assert after == before


def test_unknown_document_still_returns_text(client, monkeypatch):
    class _GenericService(_FakeOCRService):
        def run(self, image_path):  # noqa: ARG002
            return ([{"text": "A grocery list: milk, eggs, bread",
                      "confidence": 0.9, "bbox": [0, 0, 100, 20],
                      "polygon": [[0, 0], [100, 0], [100, 20], [0, 20]]}], {})

    monkeypatch.setattr(routes, "_service", _GenericService())
    response = client.post(
        "/api/ocr",
        files={"file": ("note.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    body = response.json()
    assert body["document_type"] == "UNKNOWN"
    assert body["structured_data"] == {}
    assert "milk" in body["text"]  # raw OCR never lost