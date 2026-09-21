"""
The backend contract every provider implements.

Concrete backends implement the primitives; the batch helpers
(``upload_many`` / ``download_many``) and URI wrappers (``put`` / ``get``)
build on them here, so they come for free on every backend.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from .results import DownloadResult, UploadResult
from .uri import parse_uri

logger = logging.getLogger(__name__)

DEFAULT_PRESIGN_EXPIRY = 3600


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
        """
        Upload one file.

        :param local_path: file to upload.
        :param bucket: target bucket.
        :param key: object key; defaults to ``{prefix}{filename}``.
        :param prefix: key prefix used when ``key`` is not given.
        :param metadata: optional object metadata.
        :param delete_after: if ``True``, delete ``local_path`` after a successful upload.
        :return: the upload outcome.
        """

    @abstractmethod
    def download(self, bucket: str, key: str, local_path: Path) -> DownloadResult:
        """
        Download one object to ``local_path`` (parent dirs are created).

        :param bucket: source bucket.
        :param key: object key.
        :param local_path: destination path.
        :return: the download outcome.
        """

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool:
        """
        Return whether an object exists.

        :param bucket: bucket name.
        :param key: object key.
        :return: ``True`` if the object exists.
        """

    @abstractmethod
    def list_keys(self, bucket: str, prefix: str = "") -> list[str]:
        """
        List the keys in ``bucket`` under ``prefix``.

        :param bucket: bucket to list.
        :param prefix: key prefix to filter by.
        :return: matching keys, sorted.
        """

    @abstractmethod
    def presign_download(
        self, bucket: str, key: str, *, expires_in: int = DEFAULT_PRESIGN_EXPIRY
    ) -> str:
        """
        Return a pre-signed URL granting a time-limited ``GET`` of ``bucket/key``.

        The holder can download over plain HTTP without credentials until it expires.

        :param bucket: source bucket.
        :param key: object key.
        :param expires_in: URL lifetime in seconds.
        :return: the pre-signed download URL.
        """

    @abstractmethod
    def presign_upload(
        self, bucket: str, key: str, *, expires_in: int = DEFAULT_PRESIGN_EXPIRY
    ) -> str:
        """
        Return a pre-signed URL granting a time-limited ``PUT`` to ``bucket/key``.

        The holder can upload to exactly that key over plain HTTP without
        credentials until it expires.

        :param bucket: target bucket.
        :param key: object key.
        :param expires_in: URL lifetime in seconds.
        :return: the pre-signed upload URL.
        """

    def upload_many(
        self,
        local_paths: list[Path],
        bucket: str,
        *,
        prefix: str = "",
        metadata: dict[str, str] | None = None,
        delete_after: bool = False,
    ) -> list[UploadResult]:
        """
        Upload several files, one result per file.

        Never raises on a single failure, so the caller can inspect partial success.

        :param local_paths: files to upload.
        :param bucket: target bucket.
        :param prefix: key prefix applied to every file.
        :param metadata: optional metadata applied to every object.
        :param delete_after: if ``True``, delete each file after its successful upload.
        :return: one result per input file, in order.
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

        :param bucket: source bucket.
        :param keys: object keys to download.
        :param local_dir: destination directory.
        :return: one result per key, in order.
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
        """
        Upload, addressing the target as a single ``s3://bucket/key`` URI.

        :param local_path: file to upload.
        :param uri: destination URI.
        :param metadata: optional object metadata.
        :param delete_after: if ``True``, delete ``local_path`` after a successful upload.
        :return: the upload outcome.
        """
        bucket, key = parse_uri(uri)
        return self.upload(
            Path(local_path),
            bucket,
            key=key,
            metadata=metadata,
            delete_after=delete_after,
        )

    def get(self, uri: str, local_path: Path) -> DownloadResult:
        """
        Download, addressing the source as a single ``s3://bucket/key`` URI.

        :param uri: source URI.
        :param local_path: destination path.
        :return: the download outcome.
        """
        bucket, key = parse_uri(uri)
        return self.download(bucket, key, Path(local_path))

    def presign_get(self, uri: str, *, expires_in: int = DEFAULT_PRESIGN_EXPIRY) -> str:
        """
        Pre-signed download URL, addressing the object as a single URI.

        :param uri: object URI.
        :param expires_in: URL lifetime in seconds.
        :return: the pre-signed download URL.
        """
        bucket, key = parse_uri(uri)
        return self.presign_download(bucket, key, expires_in=expires_in)

    def presign_put(self, uri: str, *, expires_in: int = DEFAULT_PRESIGN_EXPIRY) -> str:
        """
        Pre-signed upload URL, addressing the target as a single URI.

        :param uri: object URI.
        :param expires_in: URL lifetime in seconds.
        :return: the pre-signed upload URL.
        """
        bucket, key = parse_uri(uri)
        return self.presign_upload(bucket, key, expires_in=expires_in)


def _log_batch(op: str, results: list) -> None:
    n_ok = sum(bool(r) for r in results)
    logger.info("%s: %d / %d succeeded.", op, n_ok, len(results))
