"""Prompt construction for AI-assisted document drafting and revision."""

from __future__ import annotations

from tessera_core.ports.providers import LLMProvider

LANGUAGE_MATCH_RULE = (
    "Respond in the same language as the user's instruction. If no instruction "
    "is given, respond in the same language as the provided content."
)


async def generate_draft(
    prompt: str,
    llm_provider: LLMProvider,
    previous_suggestion: str | None = None,
) -> str:
    """Generate (or refine) a markdown draft for the document-creation form."""
    parts = [
        LANGUAGE_MATCH_RULE,
        "You are drafting the initial markdown content for a new document. Write "
        "clear, well-structured markdown based on the user's prompt below. Return "
        "only the markdown content, with no preamble or commentary.",
        f"User's prompt: {prompt}",
    ]
    if previous_suggestion:
        parts.append(
            "A previous draft was already generated below. Treat the user's prompt "
            "above as a follow-up instruction to revise that draft, not a new topic.\n\n"
            f"Previous draft:\n{previous_suggestion}"
        )
    system_prompt = "\n\n".join(parts)
    return await llm_provider.complete(
        messages=[{"role": "user", "content": prompt}],
        system=system_prompt,
    )


async def generate_revision(
    content: str,
    instruction: str,
    llm_provider: LLMProvider,
    previous_suggestion: str | None = None,
) -> str:
    """Generate (or refine) a revision suggestion for existing document content."""
    parts = [
        "You are proposing a revised version of the content below. Return only the "
        "revised content, with no preamble or commentary.",
    ]
    if instruction.strip():
        parts.append(LANGUAGE_MATCH_RULE)
        parts.append(f"Instruction: {instruction}")
    else:
        parts.append(LANGUAGE_MATCH_RULE)
        parts.append(
            "No specific instruction was given — perform a general improvement pass "
            "(clarity, grammar, structure) while preserving the original meaning."
        )
    parts.append(f"Content to revise:\n{content}")
    if previous_suggestion:
        parts.append(
            "A previous suggestion was already proposed below. Treat the instruction "
            "above as a follow-up refinement of that suggestion, not the original content.\n\n"
            f"Previous suggestion:\n{previous_suggestion}"
        )
    system_prompt = "\n\n".join(parts)
    return await llm_provider.complete(
        messages=[{"role": "user", "content": instruction or content}],
        system=system_prompt,
    )
