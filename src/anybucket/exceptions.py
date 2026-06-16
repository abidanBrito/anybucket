"""
Exception hierarchy for anybucket.

All errors raised by the library subclass :class:`StorageError`, so callers can
catch everything with a single ``except StorageError``.

Note that upload and download *operations* do not raise on failure. Instead,
they return result objects with a ``success`` flag (see :mod:`anybucket.results`).
"""

from __future__ import annotations


class StorageError(Exception):
    """Base class for every error raised by anybucket."""


class ConfigError(StorageError):
    """Raised when connection settings are missing or invalid."""


class ProviderError(StorageError):
    """Raised when an unknown provider is requested from the factory."""


class ObjectNotFound(StorageError):
    """Raised when an object expected to exist could not be found."""
