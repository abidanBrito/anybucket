"""
Tests for ``parse_uri``.

Cover the supported URI shapes (scheme-prefixed, bare, leading-slash)
and the malformed inputs that must raise ``ConfigError``.
"""

import pytest

from anybucket import parse_uri
from anybucket.exceptions import ConfigError


@pytest.mark.parametrize(
    "uri, expected",
    [
        ("s3://bucket/key", ("bucket", "key")),
        ("s3://bucket/path/to/obj.tif", ("bucket", "path/to/obj.tif")),
        ("gs://bucket/obj", ("bucket", "obj")),
        ("minio://bucket/a/b", ("bucket", "a/b")),
        ("bucket/key", ("bucket", "key")),
        ("/bucket/path/obj", ("bucket", "path/obj")),
    ],
)
def test_parse_uri_valid(uri, expected):
    """Test that well-formed URIs parse into a ``(bucket, key)`` pair."""
    assert parse_uri(uri) == expected


@pytest.mark.parametrize("uri", ["s3://bucket", "s3://bucket/", "bucket", ""])
def test_parse_uri_missing_key_or_bucket(uri):
    """Test that URIs lacking a bucket or key raise ``ConfigError``."""
    with pytest.raises(ConfigError):
        parse_uri(uri)
