"""Reading-order reconstruction from OCR bounding boxes.

Text regions are grouped into visual lines using y-coordinate proximity,
then each line is sorted left-to-right and lines top-to-bottom. This
reconstructs logical text like:

    NAME:          AJAY SAH
    DATE OF BIRTH: 01/01/2000

as "NAME: AJAY SAH\nDATE OF BIRTH: 01/01/2000" instead of raw engine order.
"""
from __future__ import annotations

import statistics
from typing import Any


def _bbox(item: dict[str, Any]) -> list[int]:
    return item.get("bbox") or [0, 0, 0, 0]


def _y_center(item: dict[str, Any]) -> float:
    box = _bbox(item)
    return (box[1] + box[3]) / 2.0


def _height(item: dict[str, Any]) -> float:
    box = _bbox(item)
    return max(1.0, float(box[3] - box[1]))


def group_into_lines(
    items: list[dict[str, Any]], y_tolerance: float | None = None
) -> list[list[dict[str, Any]]]:
    """Group regions into lines by vertical overlap of their centers."""
    items = [it for it in items if str(it.get("text", "")).strip()]
    if not items:
        return []
    if y_tolerance is None:
        heights = [_height(it) for it in items]
        y_tolerance = max(8.0, 0.6 * statistics.median(heights))

    ordered = sorted(items, key=lambda it: (_y_center(it), _bbox(it)[0]))
    lines: list[list[dict[str, Any]]] = [[ordered[0]]]
    for item in ordered[1:]:
        if abs(_y_center(item) - _y_center(lines[-1][-1])) <= y_tolerance:
            lines[-1].append(item)
        else:
            lines.append([item])
    for line in lines:
        line.sort(key=lambda it: _bbox(it)[0])
    return lines


def reconstruct_text(
    items: list[dict[str, Any]],
) -> tuple[list[str], str]:
    """Return (list of line strings, full text with line breaks)."""
    lines = group_into_lines(items)
    line_texts = [
        " ".join(str(it["text"]).strip() for it in line)
        for line in lines
    ]
    line_texts = [text for text in line_texts if text]
    return line_texts, "\n".join(line_texts)