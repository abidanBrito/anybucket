"""
Parsing helpers for ``scheme://bucket/key`` storage URIs.

These back the convenience API (``put`` / ``get``) so callers can address an
object with a single string instead of separate ``bucket`` and ``key`` args.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .exceptions import ConfigError


def parse_uri(uri: str) -> tuple[str, str]:
    """
    Split a storage URI into ``(bucket, key)``.

    Accepts both the scheme-qualified form (``s3://bucket/path/to/obj``)
    and the bare ``bucket/path/to/obj`` form.

    :param uri: the storage URI to parse.
    :returns: a ``(bucket, key)`` tuple.
    :raises ConfigError: if either the bucket or the key is missing.
    """
    parsed = urlparse(uri)

    if parsed.scheme:
        bucket, key = parsed.netloc, parsed.path.lstrip("/")
    else:
        bucket, _, key = uri.lstrip("/").partition("/")

    if not bucket:
        raise ConfigError(f"URI is missing a bucket: {uri!r}")

    if not key:
        raise ConfigError(f"URI is missing an object key: {uri!r}")

    return bucket, key
