"""
Google Cloud Storage backend.

A native backend built on the official ``google-cloud-storage`` SDK.

Note that ``google-cloud-storage`` is an optional dependency; install the ``gcs``
extra (``pip install anybucket[gcs]``) to use this backend.
"""

from __future__ import annotations

import logging
from pathlib import Path

from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage

from ..base import StorageBackend
from ..config import GCSConfig
from ..mime import infer_content_type
from ..results import DownloadResult, UploadResult

logger = logging.getLogger(__name__)


class GCSBackend(StorageBackend):
    """
    Upload/download against Google Cloud Storage.

    :param config: connection settings. Build one with :meth:`GCSConfig.resolve`
        to get explicit arguments with environment fallback resolution.
    """

    def __init__(self, config: GCSConfig) -> None:
        """Open a reusable GCS client from ``config``."""
        self.config = config
        if config.credentials_path:
            self._client = storage.Client.from_service_account_json(
                config.credentials_path, project=config.project
            )
        else:
            self._client = storage.Client(project=config.project)

    def ensure_bucket(self, bucket: str) -> None:
        """Create ``bucket`` if it does not already exist."""
        if not self._client.bucket(bucket).exists():
            logger.info("Creating bucket %r.", bucket)
            self._client.create_bucket(bucket)

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
        local_path = Path(local_path)
        object_key = key or f"{prefix}{local_path.name}"

        if not local_path.is_file():
            return UploadResult(
                success=False,
                bucket=bucket,
                key=object_key,
                local_path=local_path,
                message=f"Not a file: {local_path}",
            )

        size = local_path.stat().st_size
        logger.info(
            "Uploading %s (%.1f MB) -> gs://%s/%s",
            local_path.name,
            size / (1024**2),
            bucket,
            object_key,
        )

        blob = self._client.bucket(bucket).blob(object_key)
        if metadata:
            blob.metadata = metadata

        try:
            blob.upload_from_filename(
                str(local_path),
                content_type=infer_content_type(local_path),
            )
        except (GoogleAPIError, OSError) as exc:
            logger.exception("Upload failed for %s.", local_path)
            return UploadResult(
                success=False,
                bucket=bucket,
                key=object_key,
                local_path=local_path,
                message=str(exc),
            )

        if delete_after:
            local_path.unlink(missing_ok=True)
            logger.debug("Deleted local file %s after upload.", local_path)

        return UploadResult(success=True, bucket=bucket, key=object_key, local_path=local_path)

    def download(self, bucket: str, key: str, local_path: Path) -> DownloadResult:
        """Download one object to ``local_path`` (parent dirs are created)."""
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading gs://%s/%s -> %s", bucket, key, local_path)

        try:
            self._client.bucket(bucket).blob(key).download_to_filename(str(local_path))
        except (GoogleAPIError, OSError) as exc:
            logger.exception("Download failed for gs://%s/%s.", bucket, key)
            return DownloadResult(
                success=False,
                bucket=bucket,
                key=key,
                local_path=local_path,
                message=str(exc),
            )

        return DownloadResult(success=True, bucket=bucket, key=key, local_path=local_path)

    def exists(self, bucket: str, key: str) -> bool:
        """Return whether an object exists."""
        return self._client.bucket(bucket).blob(key).exists()

    def list_keys(self, bucket: str, prefix: str = "") -> list[str]:
        """Return the keys in ``bucket`` under ``prefix`` (sorted)."""
        blobs = self._client.list_blobs(bucket, prefix=prefix)
        return sorted(blob.name for blob in blobs)
