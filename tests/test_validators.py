"""Format validation tests. No real identity documents involved."""
from __future__ import annotations

from backend.services import validators


def test_valid_pan():
    assert validators.is_valid_pan("ABCDE1234F")
    assert validators.is_valid_pan("abcde1234f")  # normalized to upper


def test_invalid_pan():
    assert not validators.is_valid_pan("ABCDE12345")   # 5 digits
    assert not validators.is_valid_pan("ABCD1234F")    # 4 letters
    assert not validators.is_valid_pan("ABCDE1234")    # missing letter
    assert not validators.is_valid_pan("123451234A")   # digits in letter slots


def test_pan_candidate_ocr_confusions():
    # Classic OCR confusions are only fixed when the result is a valid PAN.
    assert validators.pan_candidate("ABCDE1234F") == "ABCDE1234F"
    assert validators.pan_candidate("ABCDE12S4F") == "ABCDE1254F"   # S -> 5
    assert validators.pan_candidate("AB0DE1234F") == "AB0DE1234F"   # letter slot O is legal
    assert validators.pan_candidate("NOTAPANXX1") is None           # never invented
    assert validators.pan_candidate("ABCDE1234") is None            # too short


def test_aadhaar_format():
    assert validators.is_valid_aadhaar("1234 5678 9012")
    assert validators.is_valid_aadhaar("123456789012")
    assert not validators.is_valid_aadhaar("1234 5678 901")   # 11 digits
    assert not validators.is_valid_aadhaar("1234-5678-901X")
    # 12 digits is only a format match, never authenticity proof.
    assert validators.format_aadhaar("123456789012") == "1234 5678 9012"


def test_date_validation():
    assert validators.normalize_date("01/01/2000") == "01/01/2000"
    assert validators.normalize_date("01-01-2000") == "01/01/2000"
    assert validators.normalize_date("01.01.2000") == "01/01/2000"
    assert validators.normalize_date("DOB: 15/08/1947") == "15/08/1947"
    assert validators.normalize_date("32/01/2000") is None    # impossible day
    assert validators.normalize_date("01/13/2000") is None    # impossible month
    assert validators.normalize_date("no date here") is None


def test_other_formats():
    assert validators.is_valid_gstin("22ABCDE1234F1Z5")
    assert validators.is_valid_passport_number("Z1234567")
    assert not validators.is_valid_passport_number("12345678")
    assert validators.is_valid_epic("ABC1234567")
    assert validators.is_valid_driving_licence("MH0120141234567")