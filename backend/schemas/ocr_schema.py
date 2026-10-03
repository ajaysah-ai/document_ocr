"""Pydantic models for every API response.

JSON serialization safety: every model uses native Python types only; all
NumPy arrays/scalars are converted to lists/floats/integers before models
are constructed (see api/routes.py and services/ocr_service.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

DISCLAIMER = (
    "This system extracts visible text from document images using OCR. "
    "It does NOT verify document authenticity and does not perform any "
    "government, bank, or issuer verification. Confidence scores reflect "
    "OCR recognition quality only, and structured extraction may be wrong "
    "even when the raw OCR is correct."
)


class HealthResponse(BaseModel):
    status: str
    ocr: str
    version: str | None = None


class FieldValue(BaseModel):
    value: str
    confidence: float = 0.0
    source: str = "ocr"
    validated: bool = False
    needs_review: bool = False


class TextRegion(BaseModel):
    text: str
    confidence: float
    bbox: list[int] = Field(default_factory=list)  # [x_min, y_min, x_max, y_max]
    polygon: list[list[int]] = Field(default_factory=list)  # 4 x [x, y]


class QualityReport(BaseModel):
    width: int
    height: int
    megapixels: float
    blur_score: float
    brightness: float
    contrast: float
    is_acceptable: bool
    warnings: list[str] = Field(default_factory=list)


class PageResult(BaseModel):
    page_index: int
    text: str
    regions: list[TextRegion] = Field(default_factory=list)


class OCRResponse(BaseModel):
    success: bool = True
    file_name: str
    document_type: str = "UNKNOWN"
    document_confidence: float = 0.0
    quality: QualityReport | None = None
    text: str = ""                       # raw OCR text in reading order
    pages: list[PageResult] = Field(default_factory=list)
    regions: list[TextRegion] = Field(default_factory=list)  # boxes + polygons
    structured_data: dict[str, FieldValue] = Field(default_factory=dict)
    processed_image_b64: str | None = None  # preprocessed image for overlay mode
    processing_time_ms: int = 0
    disclaimer: str = DISCLAIMER