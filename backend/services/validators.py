"""Format / rule validators.

IMPORTANT: validation here means FORMAT validation only (regex, digit
counts, date ranges). It is NOT government verification and says nothing
about document authenticity.
"""
from __future__ import annotations

import re

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_PATTERN = re.compile(r"^[0-9]{12}$")
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")
PASSPORT_PATTERN = re.compile(r"^[A-Z][0-9]{7}$")
EPIC_PATTERN = re.compile(r"^[A-Z]{3}[0-9]{7}$")
DRIVING_LICENCE_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[0-9]{4}[0-9]{7}$")

# Common OCR character confusions, applied ONLY to full-length candidates
# and only accepted if the result then matches the strict pattern.
_OCR_DIGIT_FIXES = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "G": "6"})
_OCR_LETTER_FIXES = str.maketrans({"0": "O", "5": "S", "8": "B", "1": "I", "2": "Z", "6": "G"})

_DATE_PATTERN = re.compile(r"\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b")


def clean_alnum(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def is_valid_pan(value: str) -> bool:
    """Strict PAN format check: 5 letters + 4 digits + 1 letter."""
    return bool(PAN_PATTERN.match(clean_alnum(value)))


def pan_candidate(value: str) -> str | None:
    """Return a valid PAN string extracted from `value`, else None.

    Never blindly converts arbitrary text into a PAN: the candidate must
    have exactly 10 alphanumeric chars and match the strict pattern either
    directly or after fixing classic OCR confusions (O->0, S->5, ...).
    """
    cleaned = clean_alnum(value)
    if len(cleaned) != 10:
        return None
    if PAN_PATTERN.match(cleaned):
        return cleaned
    fixed = cleaned.translate(_OCR_DIGIT_FIXES)
    if PAN_PATTERN.match(fixed):
        return fixed
    fixed = cleaned.translate(_OCR_LETTER_FIXES)
    if PAN_PATTERN.match(fixed):
        return fixed
    return None


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_valid_aadhaar(value: str) -> bool:
    """Format check only: 12 digits after removing spaces.

    A 12-digit number is NOT proof of a genuine Aadhaar number.
    """
    return bool(AADHAAR_PATTERN.match(digits_only(value)))


def format_aadhaar(value: str) -> str:
    digits = digits_only(value)
    if len(digits) != 12:
        return value.strip()
    return f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"


def normalize_date(value: str) -> str | None:
    """Normalize DD/MM/YYYY, DD-MM-YYYY or DD.MM.YYYY to DD/MM/YYYY.

    Returns None for unparseable or impossible dates.
    """
    match = _DATE_PATTERN.search(value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
        return None
    if month in {4, 6, 9, 11} and day > 30:
        return None
    return f"{day:02d}/{month:02d}/{year:04d}"


def find_date(value: str) -> str | None:
    return normalize_date(value)


def is_valid_gstin(value: str) -> bool:
    return bool(GSTIN_PATTERN.match(clean_alnum(value)))


def gstin_candidate(value: str) -> str | None:
    cleaned = clean_alnum(value)
    if GSTIN_PATTERN.match(cleaned):
        return cleaned
    fixed = cleaned.translate(_OCR_DIGIT_FIXES)
    return fixed if GSTIN_PATTERN.match(fixed) else None


def is_valid_passport_number(value: str) -> bool:
    return bool(PASSPORT_PATTERN.match(clean_alnum(value)))


def passport_candidate(value: str) -> str | None:
    cleaned = clean_alnum(value)
    if PASSPORT_PATTERN.match(cleaned):
        return cleaned
    fixed = cleaned.translate(_OCR_DIGIT_FIXES)
    return fixed if PASSPORT_PATTERN.match(fixed) else None


def is_valid_epic(value: str) -> bool:
    return bool(EPIC_PATTERN.match(clean_alnum(value)))


def epic_candidate(value: str) -> str | None:
    cleaned = clean_alnum(value)
    if EPIC_PATTERN.match(cleaned):
        return cleaned
    fixed = cleaned.translate(_OCR_DIGIT_FIXES)
    return fixed if EPIC_PATTERN.match(fixed) else None


def is_valid_driving_licence(value: str) -> bool:
    return bool(DRIVING_LICENCE_PATTERN.match(clean_alnum(value)))