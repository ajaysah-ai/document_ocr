"""Integration test against the real PaddleOCR engine.

Skipped automatically when PaddleOCR is not installed. Uses a synthetic
document rendered with OpenCV - no real Aadhaar/PAN images required.
"""
from __future__ import annotations

import pytest

pytest.importorskip("paddleocr")
cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from backend.services.document_classifier import classify_document
from backend.services.field_extractor import extract_fields
from backend.services.ocr_service import OCRService
from backend.services.reading_order import reconstruct_text


def _synthetic_document() -> bytes:
    image = np.full((420, 760, 3), 250, np.uint8)
    cv2.putText(image, "INCOME TAX DEPARTMENT", (30, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(image, "PERMANENT ACCOUNT NUMBER", (30, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(image, "ABCDE1234F", (30, 210),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    cv2.putText(image, "NAME: TEST USER", (30, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


@pytest.mark.slow
def test_engine_extracts_and_structures(tmp_path):
    service = OCRService()
    service.initialize()
    if not service.ready:
        pytest.skip(f"OCR engine unavailable: {service.error}")

    image_path = tmp_path / "synthetic.png"
    image_path.write_bytes(_synthetic_document())

    items, meta = service.run(image_path)
    assert items, "OCR returned no text regions"
    assert all({"text", "confidence", "bbox", "polygon"} <= set(i) for i in items)
    assert all(isinstance(i["confidence"], float) for i in items)
    assert all(isinstance(v, int) for i in items for v in i["bbox"])

    lines, text = reconstruct_text(items)
    assert text.strip()

    doc_type, confidence = classify_document(text)
    assert doc_type == "PAN"
    assert confidence > 0.6

    fields = extract_fields(doc_type, lines, items)
    assert "pan_number" in fields