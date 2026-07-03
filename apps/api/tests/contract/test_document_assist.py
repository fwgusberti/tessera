"""Contract tests: DraftAssistRequest/Response, RevisionAssistRequest/Response models."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError


class TestDraftAssistContract:
    def test_blank_prompt_rejected(self):
        from tessera_api.routers.document_assist import DraftAssistRequest

        with pytest.raises(ValidationError):
            DraftAssistRequest(space_id=uuid.uuid4(), prompt="   ")

    def test_whitespace_only_prompt_rejected(self):
        from tessera_api.routers.document_assist import DraftAssistRequest

        with pytest.raises(ValidationError):
            DraftAssistRequest(space_id=uuid.uuid4(), prompt="\n\t")

    def test_valid_prompt_accepted(self):
        from tessera_api.routers.document_assist import DraftAssistRequest

        req = DraftAssistRequest(space_id=uuid.uuid4(), prompt="Onboarding checklist")
        assert req.prompt == "Onboarding checklist"

    def test_content_markdown_required(self):
        from tessera_api.routers.document_assist import DraftAssistResponse

        with pytest.raises(ValidationError):
            DraftAssistResponse()

        resp = DraftAssistResponse(content_markdown="# Draft")
        assert resp.content_markdown == "# Draft"


class TestRevisionAssistContract:
    def test_blank_content_rejected(self):
        from tessera_api.routers.document_assist import RevisionAssistRequest

        with pytest.raises(ValidationError):
            RevisionAssistRequest(content="   ", instruction="fix grammar")

    def test_whitespace_only_content_rejected(self):
        from tessera_api.routers.document_assist import RevisionAssistRequest

        with pytest.raises(ValidationError):
            RevisionAssistRequest(content="\n\t", instruction="fix grammar")

    def test_valid_content_with_empty_instruction_accepted(self):
        from tessera_api.routers.document_assist import RevisionAssistRequest

        req = RevisionAssistRequest(content="# Hello", instruction="")
        assert req.content == "# Hello"
        assert req.instruction == ""

    def test_suggestion_required(self):
        from tessera_api.routers.document_assist import RevisionAssistResponse

        with pytest.raises(ValidationError):
            RevisionAssistResponse()

        resp = RevisionAssistResponse(suggestion="revised text")
        assert resp.suggestion == "revised text"
