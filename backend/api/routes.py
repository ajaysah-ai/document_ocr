"""API routes: GET /api/health and POST /api/ocr.

PRODUCTION SECURITY NOTE:
- Authentication and authorization are intentionally NOT hardcoded here.
  Add a FastAPI dependency (e.g. OAuth2/JWT via `fastapi.security`) on
  POST /api/ocr before exposing this service beyond localhost.
- Uploaded files are treated as untrusted data: extension allowlist,
  size limit, content re-validation via image decoding, UUID filenames,
  and deletion immediately after processing. Identity documents are
  never stored permanently by default.
"""
from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import settings
from backend.schemas.ocr_schema import (
    HealthResponse,
    OCRResponse,
    PageResult,
    QualityReport,
    TextRegion,
)
from backend.services.document_classifier import classify_document
from backend.services.field_extractor import extract_fields
from backend.services.ocr_service import OCRService
from backend.services.preprocessing import smart_preprocess
from backend.services.reading_order import reconstruct_text
from backend.utils.image_utils import analyze_quality, decode_image, encode_image

router = APIRouter(prefix="/api", tags=["ocr"])

# Module-level singleton; initialized once at app startup (see main.py).
_service = OCRService()


def get_ocr_service() -> OCRService:
    """Indirection so tests can substitute a fake service."""
    return _service


def _paddle_version() -> str | None:
    try:
        import paddle  # type: ignore

        return str(paddle.__version__)
    except Exception:  # noqa: BLE001
        return None


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    service = get_ocr_service()
    return HealthResponse(
        status="ok",
        ocr="ready" if service.ready else "unavailable",
        version=_paddle_version(),
    )


async def _read_size_limited(file: UploadFile) -> bytes:
    """Read the upload enforcing the max size (streamed, 1 MB chunks)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the maximum size of {settings.max_file_size_mb} MB.",
            )
        chunks.append(chunk)
    await file.close()
    if not chunks:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    return b"".join(chunks)


@router.post("/ocr", response_model=OCRResponse)
async def process_document(file: UploadFile = File(...)) -> OCRResponse:
    started = time.perf_counter()
    # The client filename is display-only; it is never used for disk paths.
    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    if extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{extension or '(none)'}'. "
                f"Allowed: {sorted(settings.allowed_extensions)}"
            ),
        )

    data = await _read_size_limited(file)

    # Content validation: decoding actually verifies it is a real image.
    image = decode_image(data)
    if image is None:
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid image."
        )

    service = get_ocr_service()
    job_id = uuid.uuid4().hex
    upload_path = settings.upload_dir / f"{job_id}{extension}"
    processed_path = settings.output_dir / f"{job_id}_prep.png"

    try:
        upload_path.write_bytes(data)

        quality = analyze_quality(image)                      # quality report
        processed = smart_preprocess(image)                   # OpenCV pipeline
        processed_path.write_bytes(encode_image(processed, ".png"))

        # Ship the processed image (JPEG, capped) so the frontend can draw
        # bounding boxes that align with the coordinates we return.
        processed_b64: str | None = None
        encoded_processed = encode_image(processed, ".jpg")
        if len(encoded_processed) <= 8 * 1024 * 1024:
            processed_b64 = base64.b64encode(encoded_processed).decode("ascii")

        if not service.ready:
            raise HTTPException(
                status_code=503,
                detail=f"OCR engine is unavailable: {service.error}",
            )

        raw_items, _meta = service.run(processed_path)        # PaddleOCR
        line_texts, full_text = reconstruct_text(raw_items)   # reading order
        document_type, doc_confidence = classify_document(full_text)
        structured = extract_fields(document_type, line_texts, raw_items)

        regions = [TextRegion(**item) for item in raw_items]
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return OCRResponse(
            file_name=original_name,
            document_type=document_type,
            document_confidence=doc_confidence,
            quality=QualityReport(**quality),
            text=full_text,
            pages=[PageResult(page_index=0, text=full_text, regions=regions)],
            regions=regions,
            structured_data=structured,
            processed_image_b64=processed_b64,
            processing_time_ms=elapsed_ms,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - never leak internals as 200
        raise HTTPException(
            status_code=500, detail=f"OCR processing failed: {exc}"
        ) from exc
    finally:
        # Uploaded identity documents are never kept; temp files are removed.
        for path in (upload_path, processed_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass