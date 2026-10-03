"""Image decoding/encoding and quality analysis."""
from __future__ import annotations

import cv2
import numpy as np

from backend.config import settings


def decode_image(data: bytes) -> np.ndarray | None:
    """Decode image bytes into a BGR ndarray, or None if invalid/corrupted.

    This is also the real content validation step: a renamed .exe or HTML
    file will fail to decode even if the extension was spoofed.
    """
    if not data:
        return None
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        return None
    return image


def encode_image(image: np.ndarray, ext: str = ".png") -> bytes:
    success, encoded = cv2.imencode(ext, image)
    if not success:
        raise ValueError(f"Failed to encode image as {ext}")
    return encoded.tobytes()


def analyze_quality(image: np.ndarray) -> dict:
    """Measure resolution, blur, brightness and contrast; emit warnings.

    Images are never rejected outright - the report simply informs the
    caller about conditions that may hurt OCR accuracy.
    """
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())

    warnings: list[str] = []
    megapixels = round((width * height) / 1_000_000, 3)
    if min(width, height) < settings.min_dimension_px or megapixels < 0.25:
        warnings.append("Image resolution is too low; OCR accuracy may suffer.")
    if blur_score < settings.blur_threshold:
        warnings.append("Image appears blurry; try a sharper capture.")
    if brightness < settings.dark_threshold:
        warnings.append("Image is too dark.")
    if brightness > settings.bright_threshold:
        warnings.append("Image is overexposed.")
    # Heuristic "document may be cropped" check: strong edges touching the frame.
    edges = cv2.Canny(gray, 50, 150)
    border = np.concatenate([edges[0, :], edges[-1, :], edges[:, 0], edges[:, -1]])
    if border.size and float((border > 0).mean()) > 0.15:
        warnings.append("Document may be cropped by the image frame.")

    is_acceptable = bool(
        blur_score >= settings.blur_threshold * 0.6 and 30 < brightness < 245
    )
    return {
        "width": int(width),
        "height": int(height),
        "megapixels": megapixels,
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "is_acceptable": is_acceptable,
        "warnings": warnings,
    }