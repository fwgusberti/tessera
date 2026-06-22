"""Unit tests for build_citation — written before implementation (TDD)."""

from __future__ import annotations

import uuid

import pytest


class TestBuildCitation:
    def _call(self, chunk_row: dict) -> dict:
        from tessera_api.rag.citations import build_citation

        return build_citation(chunk_row)

    def _make_row(self, **overrides) -> dict:
        doc_id = uuid.uuid4()
        version_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        row = {
            "id": chunk_id,
            "document_id": doc_id,
            "document_version_id": version_id,
            "text": "Sample quote text for testing.",
            "score": 0.85,
        }
        row.update(overrides)
        return row

    def test_document_id_present_in_output(self):
        row = self._make_row()
        result = self._call(row)
        assert "document_id" in result

    def test_document_id_equals_str_of_input(self):
        doc_id = uuid.uuid4()
        row = self._make_row(document_id=doc_id)
        result = self._call(row)
        assert result["document_id"] == str(doc_id)

    def test_document_id_is_string(self):
        row = self._make_row()
        result = self._call(row)
        assert isinstance(result["document_id"], str)

    def test_chunk_id_present(self):
        row = self._make_row()
        result = self._call(row)
        assert "chunk_id" in result

    def test_document_version_id_present(self):
        row = self._make_row()
        result = self._call(row)
        assert "document_version_id" in result

    def test_quote_truncated_to_200(self):
        long_text = "x" * 300
        row = self._make_row(text=long_text)
        result = self._call(row)
        assert len(result["quote"]) == 200

    def test_score_present(self):
        row = self._make_row(score=0.72)
        result = self._call(row)
        assert result["score"] == 0.72
