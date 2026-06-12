"""Git/GitHub connector plugin."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterator
from uuid import UUID

from tessera_core.ports.connector import ArtifactRecord, ConnectorPlugin

MARKDOWN_EXTENSIONS = {".md", ".mdx", ".markdown"}


class GitConnector(ConnectorPlugin):
    """Fetch markdown artifacts from a Git repository."""

    def fetch_artifacts(
        self,
        connector_id: UUID,
        config: dict,
        since_version: str | None = None,
    ) -> Iterator[ArtifactRecord]:
        import git

        repo_url = config["repo_url"]
        branch = config.get("branch", "main")

        repo = git.Repo(repo_url)

        if since_version:
            yield from self._changed_since(repo, connector_id, since_version, branch)
        else:
            yield from self._all_markdown(repo, connector_id, branch)

    def current_version(self, config: dict) -> str:
        import git

        repo = git.Repo(config["repo_url"])
        branch = config.get("branch", "main")
        try:
            return repo.commit(branch).hexsha
        except Exception:
            return repo.head.commit.hexsha

    def _all_markdown(
        self, repo, connector_id: UUID, branch: str
    ) -> Iterator[ArtifactRecord]:
        try:
            commit = repo.commit(branch)
        except Exception:
            commit = repo.head.commit

        for blob in commit.tree.traverse():
            if hasattr(blob, "data_stream") and Path(blob.path).suffix in MARKDOWN_EXTENSIONS:
                content = blob.data_stream.read().decode("utf-8", errors="replace")
                yield ArtifactRecord(
                    external_id=f"{connector_id}:{blob.path}",
                    path=blob.path,
                    raw_content=content,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                    source_version=commit.hexsha,
                )

    def _changed_since(
        self, repo, connector_id: UUID, since_version: str, branch: str
    ) -> Iterator[ArtifactRecord]:
        try:
            old_commit = repo.commit(since_version)
        except Exception:
            yield from self._all_markdown(repo, connector_id, branch)
            return

        try:
            new_commit = repo.commit(branch)
        except Exception:
            new_commit = repo.head.commit

        diff = old_commit.diff(new_commit)
        changed_paths = set()
        for d in diff:
            if d.b_path and Path(d.b_path).suffix in MARKDOWN_EXTENSIONS:
                changed_paths.add(d.b_path)
            if d.a_path and Path(d.a_path).suffix in MARKDOWN_EXTENSIONS:
                changed_paths.add(d.a_path)

        for blob in new_commit.tree.traverse():
            if hasattr(blob, "data_stream") and blob.path in changed_paths:
                content = blob.data_stream.read().decode("utf-8", errors="replace")
                yield ArtifactRecord(
                    external_id=f"{connector_id}:{blob.path}",
                    path=blob.path,
                    raw_content=content,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                    source_version=new_commit.hexsha,
                )
