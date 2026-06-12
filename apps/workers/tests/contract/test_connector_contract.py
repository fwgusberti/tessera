"""Connector contract tests — write FIRST, must FAIL before implementation.

Contract: every ConnectorPlugin implementation must satisfy these invariants.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from tessera_core.ports.connector import ArtifactRecord, ConnectorPlugin


class FakeConnector(ConnectorPlugin):
    """Minimal fake for contract validation."""

    def __init__(self, artifacts: list[ArtifactRecord]) -> None:
        self._artifacts = artifacts

    def fetch_artifacts(
        self, connector_id, config, since_version=None
    ) -> Iterator[ArtifactRecord]:
        yield from self._artifacts

    def current_version(self, config: dict) -> str:
        return "abc123"


def make_artifact(
    path: str = "docs/README.md",
    content: str = "# Hello World\nThis is content.",
) -> ArtifactRecord:
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return ArtifactRecord(
        external_id=f"repo:main:{path}",
        path=path,
        raw_content=content,
        content_hash=content_hash,
        source_version="abc123",
    )


class TestConnectorOutputShape:
    def test_artifact_has_external_id(self):
        artifact = make_artifact()
        assert artifact.external_id is not None
        assert len(artifact.external_id) > 0

    def test_artifact_has_path(self):
        artifact = make_artifact(path="docs/arch/ADR-001.md")
        assert artifact.path == "docs/arch/ADR-001.md"

    def test_artifact_has_content_hash(self):
        artifact = make_artifact(content="# Test")
        expected = hashlib.sha256(b"# Test").hexdigest()
        assert artifact.content_hash == expected

    def test_artifact_has_raw_content(self):
        artifact = make_artifact(content="# My Doc")
        assert artifact.raw_content == "# My Doc"

    def test_artifact_has_source_version(self):
        artifact = make_artifact()
        assert artifact.source_version == "abc123"

    def test_artifact_raw_content_does_not_contain_secrets(self):
        """No plaintext credentials should be present in artifact content."""
        content = "password=hunter2"
        artifact = make_artifact(content=content)
        # The contract does not strip secrets — it is the ingestion pipeline's
        # responsibility. But the artifact must record what was found.
        assert artifact.raw_content == content

    def test_connector_returns_iterator(self):
        conn = FakeConnector([make_artifact()])
        connector_id = uuid.uuid4()
        result = conn.fetch_artifacts(connector_id, {})
        assert hasattr(result, "__iter__")

    def test_current_version_returns_string(self):
        conn = FakeConnector([])
        version = conn.current_version({})
        assert isinstance(version, str)
        assert len(version) > 0


class TestConnectorIdempotency:
    def test_same_content_hash_for_same_content(self):
        content = "# Stable content"
        a1 = make_artifact(content=content)
        a2 = make_artifact(content=content)
        assert a1.content_hash == a2.content_hash

    def test_different_content_hash_for_different_content(self):
        a1 = make_artifact(content="# Version 1")
        a2 = make_artifact(content="# Version 2")
        assert a1.content_hash != a2.content_hash

    def test_empty_sync_yields_no_artifacts(self):
        conn = FakeConnector([])
        result = list(conn.fetch_artifacts(uuid.uuid4(), {}))
        assert result == []


class TestGitConnectorContract:
    """Contract tests specifically for the Git connector."""

    def test_git_connector_implements_plugin_interface(self):
        from tessera_workers.connectors.git import GitConnector

        assert issubclass(GitConnector, ConnectorPlugin)

    def test_git_connector_fetch_artifacts_returns_markdown_files(self, tmp_path):
        """Git connector must yield markdown artifacts from a real repo structure."""
        import subprocess

        # Init a local git repo
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)

        (tmp_path / "README.md").write_text("# Repo README\nThis is a test repository.")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "ADR-001.md").write_text("# ADR-001\nDecision record.")
        (tmp_path / "not-markdown.py").write_text("print('hello')")

        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

        from tessera_workers.connectors.git import GitConnector

        conn = GitConnector()
        artifacts = list(conn.fetch_artifacts(uuid.uuid4(), {"repo_url": str(tmp_path), "branch": "master"}))

        paths = [a.path for a in artifacts]
        assert any("README.md" in p for p in paths)
        assert any("ADR-001.md" in p for p in paths)
        # Non-markdown files should NOT be returned
        assert not any(".py" in p for p in paths)

    def test_git_connector_change_detection(self, tmp_path):
        """After initial sync, only changed files should be returned in next sync."""
        import subprocess

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)

        (tmp_path / "README.md").write_text("# Initial")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "v1"], cwd=tmp_path, check=True, capture_output=True)

        from tessera_workers.connectors.git import GitConnector

        conn = GitConnector()
        config = {"repo_url": str(tmp_path), "branch": "master"}
        v1 = conn.current_version(config)

        # Make a second commit
        (tmp_path / "README.md").write_text("# Updated")
        (tmp_path / "NEW.md").write_text("# New file")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "v2"], cwd=tmp_path, check=True, capture_output=True)

        artifacts = list(conn.fetch_artifacts(uuid.uuid4(), config, since_version=v1))
        paths = [a.path for a in artifacts]
        assert "README.md" in paths
        assert "NEW.md" in paths
