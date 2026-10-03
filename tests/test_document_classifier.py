"""Rule-based classification tests."""
from __future__ import annotations

from backend.services.document_classifier import classify_document


def test_pan():
    text = "INCOME TAX DEPARTMENT\nGOVT OF INDIA\nPERMANENT ACCOUNT NUMBER\nABCDE1234F"
    doc_type, confidence = classify_document(text)
    assert doc_type == "PAN"
    assert confidence >= 0.8


def test_aadhaar():
    text = "GOVT OF INDIA\nAADHAAR\nUNIQUE IDENTIFICATION AUTHORITY OF INDIA"
    doc_type, _ = classify_document(text)
    assert doc_type == "AADHAAR"


def test_invoice():
    doc_type, _ = classify_document("TAX INVOICE\nGSTIN: 22ABCDE1234F1Z5\nBILL TO: ACME")
    assert doc_type == "INVOICE"


def test_vid_does_not_match_inside_words():
    doc_type, _ = classify_document("DAVID KUMAR\nPROVIDED SERVICES\nSOME RANDOM NOTE")
    assert doc_type == "UNKNOWN"


def test_unknown_when_insufficient():
    doc_type, confidence = classify_document("hello world\nnothing to see here")
    assert doc_type == "UNKNOWN"
    assert confidence == 0.0