"""Unit tests for validate_password_strength (TDD — written before implementation)."""

from __future__ import annotations

import pytest


class TestValidatePasswordStrength:
    def _call(self, password: str) -> None:
        from tessera_api.auth.password_strength import validate_password_strength

        validate_password_strength(password)

    def test_valid_password_passes(self):
        self._call("C0rrect!Horse")

    def test_valid_long_password_passes(self):
        self._call("my-super-secret-pass-123")

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="at least 8"):
            self._call("short")

    def test_exactly_7_chars_raises(self):
        with pytest.raises(ValueError, match="at least 8"):
            self._call("1234567")

    def test_exactly_8_chars_passes(self):
        self._call("Abcd1234")

    def test_common_password_raises(self):
        with pytest.raises(ValueError, match="too common"):
            self._call("password")

    def test_common_password_case_insensitive(self):
        with pytest.raises(ValueError, match="too common"):
            self._call("PASSWORD")

    def test_common_password_qwerty_raises(self):
        with pytest.raises(ValueError, match="too common"):
            self._call("qwerty12")

    def test_all_same_char_raises(self):
        with pytest.raises(ValueError, match="too simple"):
            self._call("aaaaaaaa")

    def test_all_same_digit_raises(self):
        with pytest.raises(ValueError, match="too simple"):
            self._call("11111111")

    def test_valid_8_chars_with_variety(self):
        self._call("AbCd1234")
