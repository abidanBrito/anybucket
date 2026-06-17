"""
S3-compatible backend.

A single backend serves every S3-compatible provider — AWS S3, MinIO, OVH,
Cloudflare R2, Backblaze B2, Ceph — because they differ only in ``endpoint_url``
and credentials, not in protocol.

Transfers use boto3's Transfer Manager, which streams the file in fixed-size parts
(concurrently), so the whole file is never held in memory.
"""

from __future__ import annotations

import logging
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import BotoCoreError, ClientError

from ..base import StorageBackend
from ..config import S3Config
from ..mime import infer_content_type
from ..results import DownloadResult, UploadResult

logger = logging.getLogger(__name__)

# 8 MB to keep per-part memory low
_PART_SIZE = 8 * 1024 * 1024


def default_transfer_config() -> TransferConfig:
    """Return a TransferConfig tuned for memory-efficient multipart transfers."""
    return TransferConfig(
        multipart_threshold=_PART_SIZE,
        multipart_chunksize=_PART_SIZE,
        max_concurrency=4,
        use_threads=True,
    )


class S3Backend(StorageBackend):
    """
    Upload/download against any S3-compatible endpoint.

    :param config: connection settings. Build one with :meth:`S3Config.resolve`
        to get the explicit arguments with environment fallback resolution behaviour.
    :param transfer_config: optional boto3 ``TransferConfig``. Defaults to
        :func:`default_transfer_config`.
    """

    def __init__(self, config: S3Config, transfer_config: TransferConfig | None = None) -> None:
        """Open a reusable boto3 client from ``config``."""
        self.config = config
        self._transfer = transfer_config or default_transfer_config()
        # One client, reused across all operations.
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )

    def ensure_bucket(self, bucket: str) -> None:
        """Create ``bucket`` if it does not already exist."""
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            if _status_code(exc) == 404:
                logger.info("Creating bucket %r.", bucket)
                self._client.create_bucket(Bucket=bucket)
            else:
                raise

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

        extra_args: dict = {"ContentType": infer_content_type(local_path)}
        if metadata:
            extra_args["Metadata"] = metadata

        size = local_path.stat().st_size
        logger.info(
            "Uploading %s (%.1f MB) -> s3://%s/%s",
            local_path.name,
            size / (1024**2),
            bucket,
            object_key,
        )

        try:
            self._client.upload_file(
                Filename=str(local_path),
                Bucket=bucket,
                Key=object_key,
                ExtraArgs=extra_args,
                Config=self._transfer,
                Callback=_ProgressLogger(local_path.name, size),
            )
        except (BotoCoreError, ClientError) as exc:
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

        logger.info("Downloading s3://%s/%s -> %s", bucket, key, local_path)

        try:
            self._client.download_file(
                Bucket=bucket,
                Key=key,
                Filename=str(local_path),
                Config=self._transfer,
                Callback=_ProgressLogger(key.rsplit("/", 1)[-1], self._object_size(bucket, key)),
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Download failed for s3://%s/%s.", bucket, key)
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
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            if _status_code(exc) in (403, 404):
                return False
            raise

    def list_keys(self, bucket: str, prefix: str = "") -> list[str]:
        """Return the keys in ``bucket`` under ``prefix`` (sorted)."""
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return sorted(keys)

    def _object_size(self, bucket: str, key: str) -> int:
        """Object size in bytes, or 0 if it can't be determined (progress only)."""
        try:
            head = self._client.head_object(Bucket=bucket, Key=key)
            return head.get("ContentLength", 0)
        except (BotoCoreError, ClientError):
            return 0


def _status_code(exc: ClientError) -> int:
    """Return the HTTP status code from a botocore error, or 0 if unavailable."""
    return exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)


class _ProgressLogger:
    """boto3 transfer callback that logs progress at 25% intervals (DEBUG)."""

    def __init__(self, filename: str, total_bytes: int) -> None:
        self._filename = filename
        self._total = total_bytes
        self._transferred = 0
        self._next_pct = 25

    def __call__(self, bytes_amount: int) -> None:
        if self._total <= 0:
            return
        self._transferred += bytes_amount
        pct = int(self._transferred / self._total * 100)
        if pct >= self._next_pct:
            self._next_pct = (pct // 25) * 25 + 25

            logger.debug(
                "  %s — %d%% (%d / %d MB)",
                self._filename,
                pct,
                self._transferred // (1024**2),
                self._total // (1024**2),
            )
