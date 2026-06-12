"""LLM-as-judge evaluation harness for answer quality assessment (FR-027)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EvalResult(BaseModel):
    query: str
    answer: str
    reference: str
    is_correct: bool
    score: float
    reasoning: str | None = None


async def evaluate_answer(
    query: str,
    answer: str,
    reference: str,
    llm_provider,
) -> EvalResult:
    """Use the LLM as a judge to evaluate if an answer matches the reference."""
    prompt = f"""Evaluate if the following answer correctly addresses the query and matches the reference answer.

Query: {query}

Answer: {answer}

Reference: {reference}

Respond with JSON: {{"is_correct": true/false, "score": 0.0-1.0, "reasoning": "brief explanation"}}"""

    response_text = await llm_provider.classify(prompt, max_tokens=512)

    try:
        import json

        data = json.loads(response_text.strip())
        return EvalResult(
            query=query,
            answer=answer,
            reference=reference,
            is_correct=bool(data.get("is_correct", False)),
            score=float(data.get("score", 0.0)),
            reasoning=data.get("reasoning"),
        )
    except Exception:
        return EvalResult(
            query=query,
            answer=answer,
            reference=reference,
            is_correct=False,
            score=0.0,
            reasoning="Failed to parse judge response",
        )
