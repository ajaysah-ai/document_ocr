"""Reading-order reconstruction tests with synthetic regions."""
from __future__ import annotations

from backend.services.reading_order import group_into_lines, reconstruct_text


def _item(text: str, x: int, y: int, w: int = 100, h: int = 20) -> dict:
    bbox = [x, y, x + w, y + h]
    return {
        "text": text,
        "confidence": 0.9,
        "bbox": bbox,
        "polygon": [[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]],
    }


def test_top_to_bottom_left_to_right():
    items = [_item("Second line", 0, 100), _item("A", 0, 0), _item("B", 150, 0)]
    lines, text = reconstruct_text(items)
    assert text == "A B\nSecond line"


def test_line_grouping_merges_label_and_value():
    items = [_item("NAME:", 0, 0), _item("AJAY SAH", 220, 6)]
    lines, text = reconstruct_text(items)
    assert len(lines) == 1
    assert text == "NAME: AJAY SAH"


def test_three_column_layout():
    items = [
        _item("DATE OF BIRTH:", 0, 0, w=180),
        _item("01/01/2000", 200, 4),
        _item("PAN:", 0, 60),
        _item("ABCDE1234F", 120, 64),
    ]
    _, text = reconstruct_text(items)
    assert text == "DATE OF BIRTH: 01/01/2000\nPAN: ABCDE1234F"


def test_empty_input():
    lines, text = reconstruct_text([])
    assert lines == [] and text == ""