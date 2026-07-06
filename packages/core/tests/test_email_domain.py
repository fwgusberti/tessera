"""Unit tests for the email-domain classifier — pure domain logic.

TDD: written before implementation (Constitution Principle IV).
Run: cd packages/core && .venv/bin/python -m pytest tests/test_email_domain.py -v
"""

from __future__ import annotations

from tessera_core.domain.email_domain import extract_domain, is_public_email_domain


class TestExtractDomain:
    def test_extracts_substring_after_last_at(self):
        assert extract_domain("founder@acme.example") == "acme.example"

    def test_lowercases(self):
        assert extract_domain("Founder@ACME.Example") == "acme.example"

    def test_strips_surrounding_whitespace(self):
        assert extract_domain("  founder@acme.example  ") == "acme.example"

    def test_uses_last_at_when_multiple(self):
        # A quoted local part may contain '@'; the domain is after the LAST '@'.
        assert extract_domain('"weird@local"@acme.example') == "acme.example"

    def test_returns_empty_when_no_at(self):
        assert extract_domain("not-an-email") == ""

    def test_returns_empty_for_empty_string(self):
        assert extract_domain("") == ""


class TestIsPublicEmailDomain:
    def test_true_for_gmail(self):
        assert is_public_email_domain("gmail.com") is True

    def test_true_for_outlook(self):
        assert is_public_email_domain("outlook.com") is True

    def test_true_for_common_providers(self):
        for d in ("hotmail.com", "yahoo.com", "icloud.com", "proton.me", "aol.com"):
            assert is_public_email_domain(d) is True, d

    def test_false_for_corporate_domain(self):
        assert is_public_email_domain("acme.example") is False

    def test_case_insensitive(self):
        assert is_public_email_domain("GMail.COM") is True

    def test_tolerates_leading_at(self):
        assert is_public_email_domain("@gmail.com") is True

    def test_tolerates_surrounding_whitespace(self):
        assert is_public_email_domain("  gmail.com  ") is True

    def test_false_for_empty(self):
        assert is_public_email_domain("") is False
