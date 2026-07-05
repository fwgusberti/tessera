"""Unit tests for slugify() — pure name-to-slug derivation.

TDD: written before implementation.
Run: cd packages/core && .venv/bin/python -m pytest tests/test_slug.py -v
"""

from __future__ import annotations

from tessera_core.services.slug import slugify


def test_lowercases_and_hyphenates_spaces():
    assert slugify("Marketing Ops") == "marketing-ops"


def test_strips_accents():
    assert slugify("Jurídico") == "juridico"


def test_collapses_symbols_and_repeated_hyphens():
    assert slugify("Q3 -- Campaigns!!") == "q3-campaigns"


def test_strips_leading_and_trailing_hyphens():
    assert slugify("---Ops---") == "ops"


def test_falls_back_to_space_when_result_is_empty():
    assert slugify("🎉🎉🎉") == "space"


def test_truncates_to_max_length():
    name = "x" * 150
    result = slugify(name, max_length=20)
    assert len(result) <= 20
    assert not result.endswith("-")
