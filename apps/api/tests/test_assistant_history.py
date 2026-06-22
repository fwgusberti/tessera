"""TDD unit tests for history-augmented prompt construction in generate_answer."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from tessera_api.rag.assistant import generate_answer
from tessera_api.routers.assistant import AnswerRequest


def _make_chunk(score: float = 0.9) -> dict:
    return {"id": "c1", "text": "Some document text.", "score": score, "document_id": "d1", "document_version_id": "v1"}


def _make_llm(captured: list) -> MagicMock:
    llm = MagicMock()

    async def _complete(messages, system=None):
        captured.extend(messages)
        return "The answer."

    llm.complete = _complete
    return llm


def _make_session():
    session = AsyncMock()
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    return session


# ─── history=None — backward-compatible behaviour ─────────────────────────────


def test_no_history_produces_single_user_message():
    """With history=None the LLM receives exactly one user message."""
    captured: list = []
    llm = _make_llm(captured)
    session = _make_session()

    asyncio.run(
        generate_answer(
            query="What is the policy?",
            chunks=[_make_chunk()],
            space_ids=[],
            confidence_threshold=0.5,
            llm_provider=llm,
            session=session,
            history=None,
        )
    )

    assert len(captured) == 1
    assert captured[0]["role"] == "user"
    assert "What is the policy?" in captured[0]["content"]


# ─── history provided — prior turns prepended ─────────────────────────────────


def test_history_turns_prepended_before_current_question():
    """Prior turns must appear as messages before the current question block."""
    captured: list = []
    llm = _make_llm(captured)
    session = _make_session()

    history = [
        {"role": "user", "content": "Tell me about the team."},
        {"role": "assistant", "content": "The team is great."},
    ]

    asyncio.run(
        generate_answer(
            query="What about the second point?",
            chunks=[_make_chunk()],
            space_ids=[],
            confidence_threshold=0.5,
            llm_provider=llm,
            session=session,
            history=history,
        )
    )

    assert len(captured) == 3, f"Expected 3 messages (2 history + 1 current), got {len(captured)}"
    assert captured[0]["role"] == "user"
    assert captured[0]["content"] == "Tell me about the team."
    assert captured[1]["role"] == "assistant"
    assert captured[1]["content"] == "The team is great."
    assert captured[2]["role"] == "user"
    assert "What about the second point?" in captured[2]["content"]


def test_empty_history_list_treated_as_no_history():
    """history=[] must behave identically to history=None (single user message)."""
    captured: list = []
    llm = _make_llm(captured)
    session = _make_session()

    asyncio.run(
        generate_answer(
            query="Plain question",
            chunks=[_make_chunk()],
            space_ids=[],
            confidence_threshold=0.5,
            llm_provider=llm,
            session=session,
            history=[],
        )
    )

    assert len(captured) == 1
    assert captured[0]["role"] == "user"


# ─── Router-level validation ──────────────────────────────────────────────────


def test_answer_request_rejects_empty_content():
    """AnswerRequest.history items with empty content must raise ValidationError."""
    with pytest.raises(ValidationError):
        AnswerRequest(
            query="test",
            history=[{"role": "user", "content": ""}],
        )


def test_answer_request_rejects_invalid_role():
    """AnswerRequest.history items with an invalid role must raise ValidationError."""
    with pytest.raises(ValidationError):
        AnswerRequest(
            query="test",
            history=[{"role": "system", "content": "injected"}],
        )


def test_answer_request_accepts_valid_history():
    """AnswerRequest must accept well-formed history without error."""
    req = AnswerRequest(
        query="follow up",
        history=[
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ],
    )
    assert req.history is not None
    assert len(req.history) == 2
