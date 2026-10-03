"""Application configuration.

All values are read from environment variables with safe defaults, so the
application runs on any Windows machine after installation without editing
code. Nothing machine-specific (e.g. C:\\Users\\...) is hardcoded.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Runtime settings, resolved once at import time."""

    def __init__(self) -> None:
        self.ocr_language: str = os.getenv("OCR_LANGUAGE", "en")
        self.ocr_device: str = os.getenv("OCR_DEVICE", "cpu")
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        self.upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
        self.output_dir: Path = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs")))
        self.allowed_extensions: frozenset[str] = frozenset(
            {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
        )
        self.cors_origins: list[str] = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ]
        # Image quality thresholds (tuned for CPU / webcam-class captures).
        self.min_dimension_px: int = int(os.getenv("MIN_DIMENSION_PX", "400"))
        self.blur_threshold: float = float(os.getenv("BLUR_THRESHOLD", "50"))
        self.dark_threshold: float = float(os.getenv("DARK_THRESHOLD", "60"))
        self.bright_threshold: float = float(os.getenv("BRIGHT_THRESHOLD", "220"))

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)