"""Structured extraction tests using synthetic OCR output (no real IDs)."""
from __future__ import annotations

from backend.services.field_extractor import extract_fields


def _item(text: str, x: int, y: int, confidence: float = 0.95) -> dict:
    bbox = [x, y, x + 120, y + 20]
    return {"text": text, "confidence": confidence, "bbox": bbox,
            "polygon": [[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]]}


PAN_LINES = ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "ABCDE1234F",
             "NAME: AJAY SAH", "FATHER'S NAME: RAM SAH", "01/01/2000"]
PAN_REGIONS = [_item(t, 0, i * 30) for i, t in enumerate(PAN_LINES)]


def test_pan_extraction():
    fields = extract_fields("PAN", PAN_LINES, PAN_REGIONS)
    assert fields["pan_number"]["value"] == "ABCDE1234F"
    assert fields["pan_number"]["validated"] is True
    assert fields["name"]["value"] == "AJAY SAH"
    assert fields["date_of_birth"]["value"] == "01/01/2000"


def test_pan_needs_review_flag():
    regions = [_item("ABCDE1234F", 0, 0, confidence=0.55)]
    fields = extract_fields("PAN", ["ABCDE1234F"], regions)
    assert fields["pan_number"]["needs_review"] is True


AADHAAR_LINES = ["GOVT OF INDIA", "AADHAAR", "RAM KUMAR", "DOB: 01/01/1980", "MALE",
                 "1234 5678 9012"]


def test_aadhaar_extraction():
    regions = [_item(t, 0, i * 30) for i, t in enumerate(AADHAAR_LINES)]
    fields = extract_fields("AADHAAR", AADHAAR_LINES, regions)
    assert fields["aadhaar_number"]["value"] == "1234 5678 9012"
    assert fields["gender"]["value"] == "Male"
    assert fields["date_of_birth"]["value"] == "01/01/1980"


def test_unknown_returns_no_fields():
    fields = extract_fields("UNKNOWN", ["some text"], [])
    assert fields == {}