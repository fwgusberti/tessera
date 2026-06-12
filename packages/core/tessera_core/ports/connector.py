from abc import ABC, abstractmethod
from typing import Iterator
from uuid import UUID

from tessera_core.domain.entities import SourceArtifact


class ArtifactRecord:
    """Raw record yielded by a connector plugin during sync."""

    def __init__(
        self,
        external_id: str,
        path: str,
        raw_content: str,
        content_hash: str,
        source_version: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.external_id = external_id
        self.path = path
        self.raw_content = raw_content
        self.content_hash = content_hash
        self.source_version = source_version
        self.metadata = metadata or {}


class ConnectorPlugin(ABC):
    """Port interface for connector implementations (Git, Confluence, etc.)."""

    @abstractmethod
    def fetch_artifacts(
        self, connector_id: UUID, config: dict, since_version: str | None = None
    ) -> Iterator[ArtifactRecord]:
        """Yield changed artifacts since last sync. Idempotent on same content_hash."""

    @abstractmethod
    def current_version(self, config: dict) -> str:
        """Return an opaque cursor representing the current HEAD (e.g., commit SHA)."""
