"""Unit tests for POST /v1/search error handling."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _make_app():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import create_app

    app = create_app()

    async def _noop_onboarding():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop_onboarding
    return app


def _user_info():
    uid = str(uuid.uuid4())
    return {"sub": uid, "id": uid, "email": "test@test.com", "is_admin": False}


def _auth_patch():
    return patch(
        "tessera_api.auth.oidc.require_user",
        new=AsyncMock(return_value=_user_info()),
    )


def _empty_db_patches():
    """Patch get_db + SqlSpaceRepository to return an empty space list."""
    mock_session = AsyncMock()
    mock_space_repo = MagicMock()
    mock_space_repo.list_all = AsyncMock(return_value=[])

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_session

    return (
        patch("tessera_api.adapters.database.get_db", _fake_get_db),
        patch("tessera_api.adapters.repo.SqlSpaceRepository", return_value=mock_space_repo),
    )


def test_search_returns_503_when_ollama_raises_http_status_error():
    """Ollama HTTPStatusError must produce 503, not 500."""
    from fastapi.testclient import TestClient

    app = _make_app()
    db1, db2 = _empty_db_patches()

    with (
        _auth_patch(),
        db1,
        db2,
        patch(
            "tessera_api.adapters.embeddings.OllamaEmbeddingProvider.embed",
            side_effect=httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=MagicMock(),
                response=MagicMock(),
            ),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/v1/search", json={"query": "mamadeira"})

    assert response.status_code == 503


def test_search_returns_503_when_ollama_raises_connect_error():
    """Ollama ConnectError (service down) must produce 503, not 500."""
    from fastapi.testclient import TestClient

    app = _make_app()
    db1, db2 = _empty_db_patches()

    with (
        _auth_patch(),
        db1,
        db2,
        patch(
            "tessera_api.adapters.embeddings.OllamaEmbeddingProvider.embed",
            side_effect=httpx.ConnectError("Connection refused"),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/v1/search", json={"query": "mamadeira"})

    assert response.status_code == 503


def test_search_returns_200_with_empty_results_when_no_chunks_match():
    """When no chunks match the query, response is 200 with empty results list."""
    from fastapi.testclient import TestClient

    app = _make_app()
    db1, db2 = _empty_db_patches()

    with (
        _auth_patch(),
        db1,
        db2,
        patch(
            "tessera_api.adapters.embeddings.OllamaEmbeddingProvider.embed",
            new=AsyncMock(return_value=[[0.1] * 768]),
        ),
        patch(
            "tessera_api.rag.retrieval.acl_first_search",
            new=AsyncMock(return_value=[]),
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/v1/search", json={"query": "zzz-no-match-xyz"})

    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_allowed_confidentiality_is_serialized_as_pg_array_string():
    """SqlChunkRepository.search() must pass allowed_confidentiality as {val1,val2} string."""
    from tessera_api.adapters.repo import SqlChunkRepository
    from tessera_core.domain.entities import Confidentiality

    captured_params: dict = {}

    class FakeResult:
        def __iter__(self):
            return iter([])

    class FakeSession:
        async def execute(self, sql, params=None):
            captured_params.update(params or {})
            return FakeResult()

    repo = SqlChunkRepository(FakeSession())
    asyncio.run(
        repo.search(
            query_embedding=[0.1] * 768,
            space_ids=[],
            max_confidentiality_level=Confidentiality.CONFIDENTIAL.level(),
            top_k=10,
        )
    )

    ac = captured_params.get("allowed_confidentiality", "")
    assert isinstance(ac, str), f"Expected str, got {type(ac)}: {ac!r}"
    assert ac.startswith("{") and ac.endswith("}"), f"Expected {{...}} format, got: {ac!r}"
