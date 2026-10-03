"""OpenCV preprocessing helpers.

Design rules:
- The ORIGINAL upload is never modified (routes keep bytes untouched and
  preprocessing operates on an in-memory copy).
- No single fixed pipeline: `smart_preprocess` inspects the image and
  applies only the steps likely to help (contrast, denoise, deskew,
  perspective). Hard binarization (Otsu/adaptive) is available but NOT
  applied blindly, because it destroys photos/gradients on real captures.
"""
from __future__ import annotations

import cv2
import numpy as np

TARGET_LONG_SIDE = 1600


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def upscale_if_small(gray: np.ndarray, target_long_side: int = TARGET_LONG_SIDE) -> np.ndarray:
    h, w = gray.shape[:2]
    long_side = max(h, w)
    if long_side >= target_long_side:
        return gray
    scale = target_long_side / long_side
    # Never upscale more than 2.5x - huge images only waste CPU on an 8 GB laptop.
    scale = min(scale, 2.5)
    return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)


def unsharp_mask(gray: np.ndarray, amount: float = 0.6) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (0, 0), 2.0)
    return cv2.addWeighted(gray, 1.0 + amount, blurred, -amount, 0)


def otsu_threshold(gray: np.ndarray) -> np.ndarray:
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )


def estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate document skew in degrees using minAreaRect on text pixels."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(binary > 0))
    if coords.shape[0] < 200:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    return float(angle)


def deskew(gray: np.ndarray, angle: float) -> np.ndarray:
    """Rotate the image to cancel `angle` degrees of skew."""
    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def remove_borders(gray: np.ndarray, max_crop_fraction: float = 0.08) -> np.ndarray:
    """Crop a uniform solid border (scanner black frame, white margins)."""
    h, w = gray.shape[:2]
    edges = [gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]]
    rows_top = rows_bottom = cols_left = cols_right = 0
    max_rows = int(h * max_crop_fraction)
    max_cols = int(w * max_crop_fraction)
    if float(np.std(edges[0])) < 8:
        probe = gray[:max_rows, :]
        uniform_rows = int((np.std(probe, axis=1) < 8).sum())
        rows_top = min(uniform_rows, max_rows)
    if float(np.std(edges[1])) < 8:
        probe = gray[h - max_rows:, :]
        uniform_rows = int((np.std(probe, axis=1) < 8).sum())
        rows_bottom = min(uniform_rows, max_rows)
    if float(np.std(edges[2])) < 8:
        probe = gray[:, :max_cols]
        uniform_cols = int((np.std(probe, axis=0) < 8).sum())
        cols_left = min(uniform_cols, max_cols)
    if float(np.std(edges[3])) < 8:
        probe = gray[:, w - max_cols:]
        uniform_cols = int((np.std(probe, axis=0) < 8).sum())
        cols_right = min(uniform_cols, max_cols)
    if rows_top or rows_bottom or cols_left or cols_right:
        return gray[rows_top:h - rows_bottom, cols_left:w - cols_right]
    return gray


def _order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).flatten()
    rect[0] = points[np.argmin(sums)]   # top-left
    rect[2] = points[np.argmax(sums)]   # bottom-right
    rect[1] = points[np.argmin(diffs)]  # top-right
    rect[3] = points[np.argmax(diffs)]  # bottom-left
    return rect


def correct_perspective(gray: np.ndarray) -> np.ndarray | None:
    """Attempt four-point perspective correction; None if no page found."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    edged = cv2.dilate(edged, None, iterations=2)
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    h_img, w_img = gray.shape[:2]
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(contour) > 0.25 * h_img * w_img:
            points = approx.reshape(4, 2).astype(np.float32)
            rect = _order_points(points)
            (tl, tr, br, bl) = rect
            width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
            height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
            if width < 200 or height < 200:
                return None
            dst = np.array(
                [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                dtype=np.float32,
            )
            matrix = cv2.getPerspectiveTransform(rect, dst)
            return cv2.warpPerspective(gray, matrix, (width, height))
    return None


def smart_preprocess(image: np.ndarray) -> np.ndarray:
    """Choose beneficial preprocessing steps based on image statistics.

    Returns a grayscale, optionally deskewed/de-warped image as BGR (the
    format PaddleOCR expects). No hard thresholding by default.
    """
    gray = to_grayscale(image)
    gray = upscale_if_small(gray)

    # Contrast enhancement only when the image actually needs it.
    if float(gray.std()) < 45:
        gray = apply_clahe(gray)

    # Mild denoising only for noisy (low-light / high-ISO style) captures.
    if cv2.Laplacian(gray, cv2.CV_64F).var() < 120:
        gray = denoise(gray)

    gray = unsharp_mask(gray, amount=0.4)

    # Skew correction for scanned pages.
    angle = estimate_skew_angle(gray)
    if 0.5 < abs(angle) < 10:
        gray = deskew(gray, angle)

    # Perspective / document warp correction (card photos, angled shots).
    warped = correct_perspective(gray)
    if warped is not None and warped.size > 0:
        gray = warped

    gray = remove_borders(gray)

    if gray.size == 0:  # safety: never return an empty image
        gray = to_grayscale(image)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)