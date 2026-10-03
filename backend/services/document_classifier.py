"""Rule-based document classification (no LLM needed for this).

Each document type has weighted textual signals. A type is returned only
when enough signals match; otherwise UNKNOWN is returned and the caller
must not force a classification.
"""
from __future__ import annotations

import re

SIGNALS: dict[str, list[str]] = {
    "PAN": [
        "income tax department",
        "permanent account number",
        "govt of india",
        "govt. of india",
        "signature",
    ],
    "AADHAAR": [
        "aadhaar",
        "unique identification authority",
        "uidai",
        "m aadhaar",
        "vid",
    ],
    "PASSPORT": [
        "passport",
        "republic of india",
        "type p",
        "surname",
        "given name",
    ],
    "DRIVING_LICENCE": [
        "driving licence",
        "driving license",
        "licence to drive",
        "transport department",
        "dl no",
        "dlno",
    ],
    "VOTER_ID": [
        "election commission",
        "voter id",
        "elector's identity",
        "epic no",
        "assembly constituency",
    ],
    "INVOICE": [
        "tax invoice",
        "invoice",
        "invoice no",
        "invoice number",
        "bill to",
        "gstin",
        "gst",
    ],
}

# Signals that strongly identify a document count double.
STRONG_SIGNALS = {
    "PAN": {"permanent account number", "income tax department"},
    "AADHAAR": {"aadhaar", "unique identification authority", "uidai"},
    "PASSPORT": {"passport"},
    "DRIVING_LICENCE": {"driving licence", "driving license", "licence to drive"},
    "VOTER_ID": {"election commission", "elector's identity"},
    "INVOICE": {"tax invoice", "gstin", "invoice no", "invoice number"},
}


def _signal_present(signal: str, lowered_text: str) -> bool:
    """Word-boundary aware match so 'vid' doesn't fire inside 'david'."""
    pattern = r"(?<![a-z0-9])" + re.escape(signal.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, lowered_text) is not None


def classify_document(text: str) -> tuple[str, float]:
    """Classify a document from its OCR text.

    Returns (document_type, confidence) where confidence is a heuristic
    signal-strength score, never an accuracy guarantee.
    """
    lowered = text.lower()
    scores: dict[str, int] = {}
    for doc_type, signals in SIGNALS.items():
        score = 0
        for signal in signals:
            if _signal_present(signal, lowered):
                score += 2 if signal.lower() in STRONG_SIGNALS.get(doc_type, set()) else 1
        if score > 0:
            scores[doc_type] = score
    if not scores:
        return "UNKNOWN", 0.0
    best = max(scores, key=lambda k: scores[k])
    # 1 weak hit ~ 0.65, a strong hit or 2+ hits ~ 0.85+, saturated at 0.95.
    confidence = min(0.95, 0.55 + 0.15 * scores[best])
    return best, round(confidence, 2)