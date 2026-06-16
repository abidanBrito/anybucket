"""
Result objects returned by upload/download operations.

Operations return one of these instead of raising on failure, so a caller can
process a batch and inspect partial success without wrapping every call in a
``try``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TransferResult:
    """Common fields shared by upload and download results."""

    success: bool
    bucket: str
    key: str
    local_path: Path
    message: str = ""

    @property
    def uri(self) -> str:
        """The object's ``s3://bucket/key`` URI."""
        return f"s3://{self.bucket}/{self.key}"

    def __bool__(self) -> bool:
        """Return the success flag, so ``if result:`` reads naturally."""
        return self.success


@dataclass(frozen=True)
class UploadResult(TransferResult):
    """Outcome of a single :meth:`StorageBackend.upload`."""


@dataclass(frozen=True)
class DownloadResult(TransferResult):
    """Outcome of a single :meth:`StorageBackend.download`."""
