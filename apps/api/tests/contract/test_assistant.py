"""Contract test: POST /v1/assistant/answer — always citation OR dont_know."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAssistantContract:
    def test_response_always_has_citation_or_dont_know(self):
        """Contract: every answer must contain citations OR dont_know=True."""
        from tessera_api.rag.assistant import AssistantResponse, DontKnowResponse

        # Normal answer with citations
        answer = AssistantResponse(
            answer="The onboarding process requires three steps.",
            citations=[
                {
                    "chunk_id": str(uuid.uuid4()),
                    "document_version_id": str(uuid.uuid4()),
                    "quote": "The onboarding process requires",
                    "score": 0.91,
                }
            ],
            confidence=0.91,
        )
        assert answer.answer is not None
        assert len(answer.citations) > 0
        assert answer.dont_know is False

    def test_dont_know_response_has_suggested_owner(self):
        """Contract: dont_know response must include suggested owner info."""
        from tessera_api.rag.assistant import DontKnowResponse

        response = DontKnowResponse(
            answer=None,
            dont_know=True,
            suggested_owner={"space_id": str(uuid.uuid4()), "owner": "hr@example.com"},
            confidence=0.2,
        )
        assert response.dont_know is True
        assert response.answer is None
        assert response.suggested_owner is not None

    def test_answer_with_no_citations_is_invalid(self):
        """An answer that is not dont_know must have at least one citation."""
        from tessera_api.rag.assistant import AssistantResponse
        import pydantic

        with pytest.raises((ValueError, pydantic.ValidationError)):
            AssistantResponse(answer="Some unsupported claim.", citations=[], confidence=0.95)

    def test_confidence_is_between_0_and_1(self):
        """Confidence score must be in [0, 1]."""
        from tessera_api.rag.assistant import AssistantResponse
        import pydantic

        with pytest.raises((ValueError, pydantic.ValidationError)):
            AssistantResponse(
                answer="test",
                citations=[{"chunk_id": "x", "document_version_id": "y", "quote": "q", "score": 0.5}],
                confidence=1.5,
            )
