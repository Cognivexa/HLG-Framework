"""Tests for the offline secret/API-key/password/private-key scanner."""
from __future__ import annotations

from app.security.secret_scanner import (
    CATEGORY_API_KEY,
    CATEGORY_PASSWORD,
    CATEGORY_PRIVATE_KEY,
    CATEGORY_SECRET,
    filter_by_category,
    scan_text,
)


def test_detects_aws_access_key():
    findings = scan_text('AWS_ACCESS_KEY_ID = "AKIAABCDEFGHIJKLMNOP"', "f.py")
    assert any(f.category == CATEGORY_API_KEY for f in findings)


def test_detects_prefixed_password_variable():
    # Regression test: a leading \b in the pattern used to miss "PASSWORD"
    # inside "DB_PASSWORD" because "_" is a word character, so there is no
    # word boundary immediately before "P".
    findings = scan_text('DB_PASSWORD = "SuperSecret123!"', "f.py")
    assert any(f.category == CATEGORY_PASSWORD for f in findings)


def test_detects_pem_private_key_block():
    findings = scan_text("-----BEGIN RSA PRIVATE KEY-----", "f.py")
    assert any(f.category == CATEGORY_PRIVATE_KEY for f in findings)


def test_detects_generic_high_entropy_secret():
    findings = scan_text('API_TOKEN = "aZ9x7QpL3mN8vR2sT6uW1yB4cD0eF5gH"', "f.py")
    assert any(f.category in (CATEGORY_SECRET, CATEGORY_API_KEY) for f in findings)


def test_no_false_positive_on_clean_code():
    findings = scan_text("def add(a, b):\n    return a + b\n", "f.py")
    assert findings == []


def test_filter_by_category():
    findings = scan_text('PASSWORD = "hunter2222"\nAPI_KEY = "sk-abcdefghij1234567890"', "f.py")
    passwords = filter_by_category(findings, CATEGORY_PASSWORD)
    assert passwords
    assert all(f.category == CATEGORY_PASSWORD for f in passwords)


def test_line_numbers_are_1_indexed():
    text = 'x = 1\nPASSWORD = "hunter2222"\n'
    findings = scan_text(text, "f.py")
    assert findings[0].line == 2
