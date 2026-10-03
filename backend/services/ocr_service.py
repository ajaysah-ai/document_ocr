# """Singleton PaddleOCR engine (CPU only).

# The engine is created EXACTLY ONCE at application startup and reused for
# every request - never construct PaddleOCR inside a request handler.
# CPU-only, mobile-size PP-OCRv5 models to stay within an 8 GB RAM budget.

# Supports both the PaddleOCR 3.x pipeline API (`predict()` with
# rec_texts/rec_scores/rec_polys/rec_boxes) and the legacy 2.x `.ocr()`
# output shape.
# """
# from __future__ import annotations

# import logging
# from pathlib import Path
# from typing import Any

# import numpy as np

# from backend.config import settings

# logger = logging.getLogger(__name__)


# def _to_list(value: Any) -> list:
#     """Convert NumPy arrays / scalars to native Python lists."""
#     if value is None:
#         return []
#     if isinstance(value, np.ndarray):
#         return value.tolist()
#     if isinstance(value, (list, tuple)):
#         return list(value)
#     return [value]


# class OCRService:
#     """Process-wide singleton holding the PaddleOCR engine."""

#     _instance: "OCRService | None" = None

#     def __new__(cls) -> "OCRService":
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#             cls._instance._engine = None
#             cls._instance._error: str | None = None
#         return cls._instance

#     @property
#     def ready(self) -> bool:
#         return self._engine is not None

#     @property
#     def error(self) -> str | None:
#         return self._error

#     # ---------------------------------------------------------- init ----
#     def initialize(self) -> None:
#         """Load the OCR engine once. Safe to call repeatedly."""
#         if self._engine is not None:
#             return
#         try:
#             from paddleocr import PaddleOCR
#         except ImportError as exc:  # pragma: no cover - environment issue
#             self._error = f"paddleocr is not installed: {exc}"
#             logger.error(self._error)
#             return

#         attempts: list[dict[str, Any]] = [
#             # PaddleOCR 3.x, CPU, mobile models (8 GB RAM friendly).
#             {
#                 "lang": settings.ocr_language,
#                 "device": settings.ocr_device,
#                 "use_doc_orientation_classify": True,
#                 "use_doc_unwarping": True,
#                 "use_textline_orientation": True,
#                 "text_detection_model_name": "PP-OCRv5_mobile_det",
#                 "text_recognition_model_name": "PP-OCRv5_mobile_rec",
#             },
#             # PaddleOCR 3.x defaults (if mobile model names differ).
#             {
#                 "lang": settings.ocr_language,
#                 "device": settings.ocr_device,
#                 "use_doc_orientation_classify": True,
#                 "use_doc_unwarping": True,
#                 "use_textline_orientation": True,
#             },
#             # PaddleOCR 2.x fallback.
#             {"lang": settings.ocr_language, "use_angle_cls": True, "use_gpu": False, "show_log": False},
#         ]
#         last_error: Exception | None = None
#         for kwargs in attempts:
#             try:
#                 self._engine = PaddleOCR(**kwargs)
#                 logger.info("PaddleOCR initialized with kwargs: %s", sorted(kwargs))
#                 self._error = None
#                 return
#             except Exception as exc:  # noqa: BLE001 - try next config
#                 last_error = exc
#                 logger.warning("PaddleOCR init attempt failed: %s", exc)
#         self._error = f"Could not initialize PaddleOCR: {last_error}"
#         logger.error(self._error)

#     # ---------------------------------------------------------- run -----
#     def run(self, image_path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
#         """Run OCR on an image file.

#         Returns (items, meta) where each item is:
#             {"text": str, "confidence": float,
#              "bbox": [x0, y0, x1, y1], "polygon": [[x, y] x4]}
#         All coordinates are native Python ints (JSON-serializable).
#         """
#         if not self.ready:
#             raise RuntimeError(self._error or "OCR engine is not initialized")

#         if hasattr(self._engine, "predict"):  # PaddleOCR 3.x
#             raw_pages = self._engine.predict(str(image_path))
#             items, meta = self._parse_v3(raw_pages)
#         else:  # PaddleOCR 2.x
#             raw_pages = self._engine.ocr(str(image_path), cls=True)
#             items, meta = self._parse_v2(raw_pages)

#         # Drop empty texts but NEVER drop confidence/box metadata.
#         items = [it for it in items if it["text"].strip()]
#         return items, meta

#     # ---------------------------------------------------------- v3 ------
#     @staticmethod
#     def _unwrap_page(page: Any) -> dict[str, Any]:
#         data = page
#         if hasattr(data, "json"):
#             try:
#                 data = data.json  # PaddleX result objects expose .json
#             except Exception:  # noqa: BLE001
#                 pass
#         if not isinstance(data, dict) and hasattr(data, "items"):
#             try:
#                 data = dict(data)
#             except Exception:  # noqa: BLE001
#                 pass
#         if isinstance(data, dict) and isinstance(data.get("res"), dict):
#             data = data["res"]
#         return data if isinstance(data, dict) else {}

#     def _parse_v3(self, raw_pages: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
#         items: list[dict[str, Any]] = []
#         meta: dict[str, Any] = {"engine": "paddleocr-v3"}
#         for page in raw_pages or []:
#             data = self._unwrap_page(page)
#             texts = [str(t) for t in _to_list(data.get("rec_texts"))]
#             scores = _to_list(data.get("rec_scores")) or [0.0] * len(texts)
#             polys = _to_list(data.get("rec_polys")) or _to_list(data.get("dt_polys"))
#             boxes = _to_list(data.get("rec_boxes"))
#             for index, text in enumerate(texts):
#                 poly_points = polys[index] if index < len(polys) else None
#                 if poly_points is None and index < len(boxes):
#                     x0, y0, x1, y1 = [int(v) for v in boxes[index][:4]]
#                     poly_points = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
#                 polygon = [[int(round(float(px))), int(round(float(py)))] for px, py in (poly_points or [])]
#                 if polygon:
#                     xs = [p[0] for p in polygon]
#                     ys = [p[1] for p in polygon]
#                     bbox = [min(xs), min(ys), max(xs), max(ys)]
#                 elif index < len(boxes):
#                     bbox = [int(v) for v in boxes[index][:4]]
#                     polygon = [[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]]
#                 else:
#                     bbox = [0, 0, 0, 0]
#                 try:
#                     confidence = float(scores[index])
#                 except (IndexError, TypeError, ValueError):
#                     confidence = 0.0
#                 items.append({
#                     "text": text,
#                     "confidence": round(confidence, 4),
#                     "bbox": bbox,
#                     "polygon": polygon,
#                 })
#         return items, meta

#     # ---------------------------------------------------------- v2 ------
#     @staticmethod
#     def _parse_v2(raw_pages: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
#         items: list[dict[str, Any]] = []
#         for page in raw_pages or []:
#             for entry in page or []:
#                 try:
#                     box, (text, score) = entry
#                 except (TypeError, ValueError):
#                     continue
#                 polygon = [[int(round(float(px))), int(round(float(py)))] for px, py in box]
#                 xs = [p[0] for p in polygon]
#                 ys = [p[1] for p in polygon]
#                 items.append({
#                     "text": str(text),
#                     "confidence": round(float(score), 4),
#                     "bbox": [min(xs), min(ys), max(xs), max(ys)],
#                     "polygon": polygon,
#                 })
#         return items, {"engine": "paddleocr-v2"}


"""Singleton PaddleOCR engine (CPU only).

The engine is created EXACTLY ONCE at application startup and reused for
every request - never construct PaddleOCR inside a request handler.
CPU-only, mobile-size PP-OCRv5 models to stay within an 8 GB RAM budget.

Supports both the PaddleOCR 3.x pipeline API (`predict()` with
rec_texts/rec_scores/rec_polys/rec_boxes) and the legacy 2.x `.ocr()`
output shape.
"""
from __future__ import annotations

import logging
import os  # Added to set global engine fallback flags
from pathlib import Path
from typing import Any

import numpy as np

from backend.config import settings

# Force PaddlePaddle to bypass the broken PIR API conversion layer globally
# This must be done prior to any implicit paddle submodule initialization logic
os.environ["FLAGS_enable_pir_api"] = "0"

logger = logging.getLogger(__name__)


def _to_list(value: Any) -> list:
    """Convert NumPy arrays / scalars to native Python lists."""
    if value is None:
        return []
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


class OCRService:
    """Process-wide singleton holding the PaddleOCR engine."""

    _instance: "OCRService | None" = None

    def __new__(cls) -> "OCRService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine = None
            cls._instance._error: str | None = None
        return cls._instance

    @property
    def ready(self) -> bool:
        return self._engine is not None

    @property
    def error(self) -> str | None:
        return self._error

    # ---------------------------------------------------------- init ----
    def initialize(self) -> None:
        """Load the OCR engine once. Safe to call repeatedly."""
        if self._engine is not None:
            return
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:  # pragma: no cover - environment issue
            self._error = f"paddleocr is not installed: {exc}"
            logger.error(self._error)
            return

        attempts: list[dict[str, Any]] = [
            # PaddleOCR 3.x, CPU, mobile models (8 GB RAM friendly).
            {
                "lang": settings.ocr_language,
                "device": settings.ocr_device,
                "use_doc_orientation_classify": True,
                "use_doc_unwarping": True,
                "use_textline_orientation": True,
                "text_detection_model_name": "PP-OCRv5_mobile_det",
                "text_recognition_model_name": "PP-OCRv5_mobile_rec",
                "enable_mkldnn": False,  # Bypasses the PIR ArrayAttribute compatibility crash
            },
            # PaddleOCR 3.x defaults (if mobile model names differ).
            {
                "lang": settings.ocr_language,
                "device": settings.ocr_device,
                "use_doc_orientation_classify": True,
                "use_doc_unwarping": True,
                "use_textline_orientation": True,
                "enable_mkldnn": False,  # Safety guarantee for fallback configs
            },
            # PaddleOCR 2.x fallback.
            {
                "lang": settings.ocr_language, 
                "use_angle_cls": True, 
                "use_gpu": False, 
                "show_log": False,
                "enable_mkldnn": False,  # Ensured compatibility across old architecture paths
            },
        ]
        last_error: Exception | None = None
        for kwargs in attempts:
            try:
                self._engine = PaddleOCR(**kwargs)
                logger.info("PaddleOCR initialized with kwargs: %s", sorted(kwargs))
                self._error = None
                return
            except Exception as exc:  # noqa: BLE001 - try next config
                last_error = exc
                logger.warning("PaddleOCR init attempt failed: %s", exc)
        self._error = f"Could not initialize PaddleOCR: {last_error}"
        logger.error(self._error)

    # ---------------------------------------------------------- run -----
    def run(self, image_path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Run OCR on an image file.

        Returns (items, meta) where each item is:
            {"text": str, "confidence": float,
             "bbox": [x0, y0, x1, y1], "polygon": [[x, y] x4]}
        All coordinates are native Python ints (JSON-serializable).
        """
        if not self.ready:
            raise RuntimeError(self._error or "OCR engine is not initialized")

        if hasattr(self._engine, "predict"):  # PaddleOCR 3.x
            raw_pages = self._engine.predict(str(image_path))
            items, meta = self._parse_v3(raw_pages)
        else:  # PaddleOCR 2.x
            raw_pages = self._engine.ocr(str(image_path), cls=True)
            items, meta = self._parse_v2(raw_pages)

        # Drop empty texts but NEVER drop confidence/box metadata.
        items = [it for it in items if it["text"].strip()]
        return items, meta

    # ---------------------------------------------------------- v3 ------
    @staticmethod
    def _unwrap_page(page: Any) -> dict[str, Any]:
        data = page
        if hasattr(data, "json"):
            try:
                data = data.json  # PaddleX result objects expose .json
            except Exception:  # noqa: BLE001
                pass
        if not isinstance(data, dict) and hasattr(data, "items"):
            try:
                data = dict(data)
            except Exception:  # noqa: BLE001
                pass
        if isinstance(data, dict) and isinstance(data.get("res"), dict):
            data = data["res"]
        return data if isinstance(data, dict) else {}

    def _parse_v3(self, raw_pages: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        items: list[dict[str, Any]] = []
        meta: dict[str, Any] = {"engine": "paddleocr-v3"}
        for page in raw_pages or []:
            data = self._unwrap_page(page)
            texts = [str(t) for t in _to_list(data.get("rec_texts"))]
            scores = _to_list(data.get("rec_scores")) or [0.0] * len(texts)
            polys = _to_list(data.get("rec_polys")) or _to_list(data.get("dt_polys"))
            boxes = _to_list(data.get("rec_boxes"))
            for index, text in enumerate(texts):
                poly_points = polys[index] if index < len(polys) else None
                if poly_points is None and index < len(boxes):
                    x0, y0, x1, y1 = [int(v) for v in boxes[index][:4]]
                    poly_points = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                polygon = [[int(round(float(px))), int(round(float(py)))] for px, py in (poly_points or [])]
                if polygon:
                    xs = [p[0] for p in polygon]
                    ys = [p[1] for p in polygon]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
                elif index < len(boxes):
                    bbox = [int(v) for v in boxes[index][:4]]
                    polygon = [[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]]
                else:
                    bbox = [0, 0, 0, 0]
                try:
                    confidence = float(scores[index])
                except (IndexError, TypeError, ValueError):
                    confidence = 0.0
                items.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "bbox": bbox,
                    "polygon": polygon,
                })
        return items, meta

    # ---------------------------------------------------------- v2 ------
    @staticmethod
    def _parse_v2(raw_pages: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for page in raw_pages or []:
            for entry in page or []:
                try:
                    box, (text, score) = entry
                except (TypeError, ValueError):
                    continue
                polygon = [[int(round(float(px))), int(round(float(py)))] for px, py in box]
                xs = [p[0] for p in polygon]
                ys = [p[1] for p in polygon]
                items.append({
                    "text": str(text),
                    "confidence": round(float(score), 4),
                    "bbox": [min(xs), min(ys), max(xs), max(ys)],
                    "polygon": polygon,
                })
        return items, {"engine": "paddleocr-v2"}
