"""Structured field extraction per document type.

Extractors work on reconstructed reading-order lines plus raw regions
(with confidences and positions). Every value carries the OCR confidence
of its source region; values below the review threshold are flagged.
Nothing here claims authenticity - `validated` only means the value
passed a format/rule check (see services/validators.py).
"""
from __future__ import annotations

import re
from typing import Any

from backend.services import validators

REVIEW_CONFIDENCE_THRESHOLD = 0.70


def _field(value: str, confidence: float, validated: bool = False) -> dict[str, Any]:
    confidence = round(float(confidence), 4)
    return {
        "value": value,
        "confidence": confidence,
        "source": "ocr",
        "validated": bool(validated),
        "needs_review": confidence < REVIEW_CONFIDENCE_THRESHOLD,
    }


def _best_region_match(
    regions: list[dict[str, Any]], matcher
) -> tuple[str, float] | None:
    """Return (normalized_value, confidence) of the highest-confidence
    region whose text `matcher` accepts; matcher returns the normalized
    value or None."""
    best: tuple[str, float] | None = None
    for region in regions:
        normalized = matcher(str(region.get("text", "")))
        if normalized is None:
            continue
        confidence = float(region.get("confidence", 0.0))
        if best is None or confidence > best[1]:
            best = (normalized, confidence)
    return best


def _value_after_label(lines: list[str], label_patterns: list[str]) -> tuple[str, float] | None:
    """Find 'LABEL: value' either inline in a line or on the following line."""
    patterns = [re.compile(p, re.IGNORECASE) for p in label_patterns]
    for index, line in enumerate(lines):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                value = match.group(1).strip(" :-\t") if match.groups() else ""
                if value:
                    return value, 0.9
                # Value may sit on the next line.
                if index + 1 < len(lines):
                    nxt = lines[index + 1].strip()
                    if nxt and not any(p.search(nxt) for p in patterns):
                        return nxt, 0.85
    return None


def _find_date_field(lines: list[str], extra_labels: list[str] | None = None) -> tuple[str, float] | None:
    label_names = ["date of birth", "dob", "birth date"] + list(extra_labels or [])
    label_alt = "|".join(label_names)
    after_label = _value_after_label(lines, [rf"(?:{label_alt})[\s:.-]*(.+)"])
    candidates: list[tuple[str, float]] = []
    if after_label:
        normalized = validators.find_date(after_label[0])
        if normalized:
            candidates.append((normalized, after_label[1]))
    for line in lines:
        normalized = validators.find_date(line)
        if normalized:
            candidates.append((normalized, 0.7))
    return max(candidates, key=lambda c: c[1]) if candidates else None


# ---------------------------------------------------------------- PAN ----

def extract_pan(lines: list[str], regions: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    pan = _best_region_match(regions, validators.pan_candidate)
    if pan:
        fields["pan_number"] = _field(pan[0], pan[1], validated=True)

    name = _value_after_label(lines, [r"^name[\s:.-]+(.+)$", r"\bname\b[\s:.-]+([A-Za-z .]+)$"])
    if name:
        fields["name"] = _field(name[0], name[1])

    fathers_name = _value_after_label(
        lines, [r"father'?s name[\s:.-]+(.+)", r"father[\s:.-]+(.+)"]
    )
    if fathers_name:
        fields["fathers_name"] = _field(fathers_name[0], fathers_name[1])

    dob = _find_date_field(lines)
    if dob:
        fields["date_of_birth"] = _field(dob[0], dob[1], validated=True)
    return fields


# ------------------------------------------------------------ Aadhaar ----

_AADHAAR_RE = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
_AADHAAR_PLAIN_RE = re.compile(r"\b(\d{12})\b")


def _aadhaar_matcher(text: str) -> str | None:
    match = _AADHAAR_RE.search(text) or _AADHAAR_PLAIN_RE.search(text)
    if not match:
        return None
    value = match.group(1)
    return validators.format_aadhaar(value) if validators.is_valid_aadhaar(value) else None


def extract_aadhaar(lines: list[str], regions: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    number = _best_region_match(regions, _aadhaar_matcher)
    if number:
        # Confidence: OCR confidence only. 12 digits is a FORMAT match,
        # never proof of a genuine Aadhaar number.
        fields["aadhaar_number"] = _field(number[0], number[1], validated=True)

    name = _value_after_label(lines, [r"^name[\s:.-]+(.+)$"])
    if name:
        fields["name"] = _field(name[0], name[1])

    dob = _find_date_field(lines, extra_labels=["year of birth", r"\byob\b"])
    if dob:
        fields["date_of_birth"] = _field(dob[0], dob[1], validated=True)

    for line in lines:
        lowered = line.lower()
        if re.search(r"\bmale\b", lowered) and "female" not in lowered:
            fields["gender"] = _field("Male", 0.9, validated=True)
            break
        if re.search(r"\bfemale\b", lowered):
            fields["gender"] = _field("Female", 0.9, validated=True)
            break
    return fields


# ------------------------------------------------------------ Passport ---

def extract_passport(lines: list[str], regions: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    number = _best_region_match(regions, validators.passport_candidate)
    if number:
        fields["passport_number"] = _field(number[0], number[1], validated=True)
    surname = _value_after_label(lines, [r"surname[\s:.-]+(.+)"])
    if surname:
        fields["surname"] = _field(surname[0], surname[1])
    given = _value_after_label(lines, [r"given name(?:s)?[\s:.-]+(.+)"])
    if given:
        fields["given_names"] = _field(given[0], given[1])
    nationality = _value_after_label(lines, [r"nationality[\s:.-]+(.+)"])
    if nationality:
        fields["nationality"] = _field(nationality[0], nationality[1])
    dob = _find_date_field(lines)
    if dob:
        fields["date_of_birth"] = _field(dob[0], dob[1], validated=True)
    expiry = _value_after_label(lines, [r"(?:date of expiry|expiry)[\s:.-]+(.+)"])
    if expiry:
        normalized = validators.find_date(expiry[0])
        if normalized:
            fields["date_of_expiry"] = _field(normalized, expiry[1], validated=True)
    return fields


# ---------------------------------------------------- Driving licence ----

def _dl_matcher(text: str) -> str | None:
    cleaned = validators.clean_alnum(text)
    if validators.is_valid_driving_licence(cleaned):
        return cleaned
    fixed = cleaned.translate(str.maketrans({"O": "0", "Q": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2"}))
    if validators.is_valid_driving_licence(fixed):
        return fixed
    return None


def extract_driving_licence(lines: list[str], regions: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    number = _best_region_match(regions, _dl_matcher)
    if number:
        fields["dl_number"] = _field(number[0], number[1], validated=True)
    name = _value_after_label(lines, [r"^name[\s:.-]+(.+)$"])
    if name:
        fields["name"] = _field(name[0], name[1])
    dob = _find_date_field(lines)
    if dob:
        fields["date_of_birth"] = _field(dob[0], dob[1], validated=True)
    validity = _value_after_label(lines, [r"(?:valid(?:ity)?(?: upto| until)?)[\s:.-]+(.+)"])
    if validity:
        normalized = validators.find_date(validity[0])
        if normalized:
            fields["validity"] = _field(normalized, validity[1], validated=True)
    return fields


# ------------------------------------------------------------- Voter ID --

def extract_voter_id(lines: list[str], regions: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    epic = _best_region_match(regions, validators.epic_candidate)
    if epic:
        fields["epic_number"] = _field(epic[0], epic[1], validated=True)
    name = _value_after_label(
        lines, [r"(?:elector'?s name|name)[\s:.-]+(.+)"]
    )
    if name:
        fields["name"] = _field(name[0], name[1])
    fathers_name = _value_after_label(lines, [r"father'?s name[\s:.-]+(.+)"])
    if fathers_name:
        fields["fathers_name"] = _field(fathers_name[0], fathers_name[1])
    return fields


# -------------------------------------------------------------- Invoice --

_INVOICE_NO = re.compile(
    r"(?:invoice\s*(?:no\.?|number|#)|bill\s*no\.?|inv\s*no\.?)[\s:.-]*([A-Za-z0-9/_-]+)",
    re.IGNORECASE,
)
_TOTAL = re.compile(
    r"(?:grand\s*total|total\s*(?:due|amount)?|amount\s*due|balance\s*due)"
    r"[\s:.-]*(?:rs\.?|inr)?[\s:.-]*([0-9][0-9,]*\.?\d{0,2})",
    re.IGNORECASE,
)


def extract_invoice(lines: list[str], regions: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    joined = "\n".join(lines)

    number = _value_after_label(lines, [r"(?:invoice\s*(?:no\.?|number|#)|bill\s*no\.?)[\s:.-]+(.+)"])
    if not number:
        match = _INVOICE_NO.search(joined)
        if match:
            number = (match.group(1), 0.85)
    if number:
        fields["invoice_number"] = _field(number[0], number[1])

    invoice_date = _value_after_label(lines, [r"(?:invoice\s*)?date[\s:.-]+(.+)"])
    if invoice_date:
        normalized = validators.find_date(invoice_date[0])
        if normalized:
            fields["invoice_date"] = _field(normalized, invoice_date[1], validated=True)
    if "invoice_date" not in fields:
        generic = _find_date_field(lines)
        if generic:
            fields["invoice_date"] = _field(generic[0], generic[1], validated=True)

    total = _TOTAL.search(joined.replace(",", ""))
    if total:
        fields["total_amount"] = _field(total.group(1), 0.8)

    gstin = _best_region_match(regions, validators.gstin_candidate)
    if gstin:
        fields["gstin"] = _field(gstin[0], gstin[1], validated=True)

    # Vendor: first substantive line that is not a keyword label.
    keywords = ("invoice", "bill", "gst", "tax", "date", "no", "total", "amount")
    for line in lines:
        cleaned = line.strip()
        lowered = cleaned.lower()
        if len(cleaned) < 4 or any(lowered.startswith(k) for k in keywords):
            continue
        fields["vendor"] = _field(cleaned, 0.7)
        break
    return fields


EXTRACTORS = {
    "PAN": extract_pan,
    "AADHAAR": extract_aadhaar,
    "PASSPORT": extract_passport,
    "DRIVING_LICENCE": extract_driving_licence,
    "VOTER_ID": extract_voter_id,
    "INVOICE": extract_invoice,
}


def extract_fields(
    document_type: str,
    lines: list[str],
    regions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Dispatch to the right extractor; UNKNOWN documents get no fields
    but still keep their raw OCR text and regions."""
    extractor = EXTRACTORS.get(document_type)
    if extractor is None:
        return {}
    return extractor(lines, regions)