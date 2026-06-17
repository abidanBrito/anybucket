"""
Top-level package for the anybucket library.

Provides a simple, unified interface over object-storage buckets.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .backends import S3Backend
from .base import StorageBackend
from .config import GCSConfig, S3Config
from .exceptions import (
    ConfigError,
    ObjectNotFound,
    ProviderError,
    StorageError,
)
from .factory import Provider, get_client
from .results import DownloadResult, UploadResult
from .uri import parse_uri

try:
    from .backends.gcs import GCSBackend
except ImportError:
    GCSBackend = None

try:
    __version__ = version("anybucket")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__author__ = "Abidán Brito <abidan.brito@gmail.com>"
__copyright__ = "Copyright 2026, Abidán Brito"

__all__ = [
    "get_client",
    "Provider",
    "StorageBackend",
    "S3Backend",
    "GCSBackend",
    "S3Config",
    "GCSConfig",
    "UploadResult",
    "DownloadResult",
    "parse_uri",
    "StorageError",
    "ConfigError",
    "ProviderError",
    "ObjectNotFound",
    "__version__",
]
