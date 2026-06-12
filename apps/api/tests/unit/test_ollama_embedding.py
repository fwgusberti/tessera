"""Unit tests for OllamaEmbeddingProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tessera_api.adapters.embeddings import OllamaEmbeddingProvider


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from tessera_api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_dimensions_property_returns_768(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    provider = OllamaEmbeddingProvider()
    assert provider.dimensions == 768


@pytest.mark.anyio
async def test_embed_passes_model_and_texts_in_body(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"embeddings": [[0.1] * 768]}

    captured = {}

    async def fake_post(path, *, json=None, **kwargs):
        captured["path"] = path
        captured["json"] = json
        return fake_response

    mock_client = AsyncMock()
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        provider = OllamaEmbeddingProvider()
        await provider.embed(["hello world"])

    assert captured["json"]["model"] == "nomic-embed-text"
    assert captured["json"]["input"] == ["hello world"]


@pytest.mark.anyio
async def test_embed_returns_embeddings_from_response(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    expected = [[0.1] * 768]

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"embeddings": expected}

    async def fake_post(path, *, json=None, **kwargs):
        return fake_response

    mock_client = AsyncMock()
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        provider = OllamaEmbeddingProvider()
        result = await provider.embed(["hello world"])

    assert result == expected
    assert len(result[0]) == 768


@pytest.mark.anyio
async def test_embed_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(),
    )

    async def fake_post(path, *, json=None, **kwargs):
        return fake_response

    mock_client = AsyncMock()
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        provider = OllamaEmbeddingProvider()
        with pytest.raises(httpx.HTTPStatusError):
            await provider.embed(["hello"])
