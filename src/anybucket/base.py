"""
The backend contract every provider implements.

The interface is deliberately small: a concrete backend only has to implement
the four primitives (:meth:`upload`, :meth:`download`, :meth:`exists`,
:meth:`list`).

Batch helpers (``upload_many`` / ``download_many``) and URI convenience
wrappers (``put`` / ``get``) are provided here in terms of those primitives,
so they come for free on every future backend.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from .results import DownloadResult, UploadResult
from .uri import parse_uri

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base for a single object-storage provider."""

    @abstractmethod
    def upload(
        self,
        local_path: Path,
        bucket: str,
        key: str | None = None,
        *,
        prefix: str = "",
        metadata: dict[str, str] | None = None,
        delete_after: bool = False,
    ) -> UploadResult:
        """Upload one file. ``key`` defaults to ``{prefix}{filename}``."""

    @abstractmethod
    def download(self, bucket: str, key: str, local_path: Path) -> DownloadResult:
        """Download one object to ``local_path`` (parent dirs are created)."""

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool:
        """Return whether an object exists."""

    @abstractmethod
    def list_keys(self, bucket: str, prefix: str = "") -> list[str]:
        """Return the keys in ``bucket`` under ``prefix`` (sorted)."""

    def upload_many(
        self,
        local_paths: list[Path],
        bucket: str,
        *,
        prefix: str = "",
        metadata: dict[str, str] | None = None,
        delete_after: bool = False,
    ) -> list[UploadResult]:
        """Upload several files, one result per file.

        Never raises on a single failure, so the caller can inspect partial
        success.
        """
        results = [
            self.upload(
                path,
                bucket,
                prefix=prefix,
                metadata=metadata,
                delete_after=delete_after,
            )
            for path in local_paths
        ]
        _log_batch("upload_many", results)
        return results

    def download_many(self, bucket: str, keys: list[str], local_dir: Path) -> list[DownloadResult]:
        """
        Download several objects into ``local_dir``, one result per key.

        The local filename is the last path segment of each key.
        """
        local_dir = Path(local_dir)
        results = [self.download(bucket, key, local_dir / key.rsplit("/", 1)[-1]) for key in keys]
        _log_batch("download_many", results)
        return results

    def put(
        self,
        local_path: Path,
        uri: str,
        *,
        metadata: dict[str, str] | None = None,
        delete_after: bool = False,
    ) -> UploadResult:
        """Upload addressing the target as a single ``s3://bucket/key`` URI."""
        bucket, key = parse_uri(uri)
        return self.upload(
            Path(local_path),
            bucket,
            key=key,
            metadata=metadata,
            delete_after=delete_after,
        )

    def get(self, uri: str, local_path: Path) -> DownloadResult:
        """Download addressing the source as a single ``s3://bucket/key`` URI."""
        bucket, key = parse_uri(uri)
        return self.download(bucket, key, Path(local_path))


def _log_batch(op: str, results: list) -> None:
    n_ok = sum(bool(r) for r in results)
    logger.info("%s: %d / %d succeeded.", op, n_ok, len(results))
