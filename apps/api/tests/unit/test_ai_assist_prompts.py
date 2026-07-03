"""Unit tests for ai_assist.prompts — draft/revision prompt construction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.anyio
async def test_generate_draft_includes_previous_suggestion_on_refinement():
    from tessera_api.ai_assist.prompts import generate_draft

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="# Refined draft")

    result = await generate_draft(
        prompt="make it shorter",
        llm_provider=mock_llm,
        previous_suggestion="# Original draft",
    )

    assert result == "# Refined draft"
    system = mock_llm.complete.call_args.kwargs["system"]
    assert "# Original draft" in system
    assert "make it shorter" in system


@pytest.mark.anyio
async def test_generate_revision_includes_previous_suggestion_on_refinement():
    from tessera_api.ai_assist.prompts import generate_revision

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Refined suggestion")

    result = await generate_revision(
        content="Original content.",
        instruction="even shorter",
        llm_provider=mock_llm,
        previous_suggestion="First suggestion.",
    )

    assert result == "Refined suggestion"
    system = mock_llm.complete.call_args.kwargs["system"]
    assert "First suggestion." in system
    assert "Instruction: even shorter" in system
