"""
Live integration tests against a real MinIO server.

Unlike ``test_s3_backend.py`` (which uses the ``moto`` emulator), these talk to
an actual S3-compatible server. They are the only tests that exercise:

* a genuine network round-trip against a real endpoint, and
* the boto3 multipart transfer path

They are skipped unless ``MINIO_TEST_ENDPOINT`` is set, e.g.::

    MINIO_TEST_ENDPOINT=http://localhost:9000 uv run pytest tests/test_minio_integration.py
"""

from __future__ import annotations

import os
import uuid
from typing import cast

import pytest

from anybucket import S3Backend, get_client

ENDPOINT = os.environ.get("MINIO_TEST_ENDPOINT")
ACCESS_KEY = os.environ.get("MINIO_TEST_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.environ.get("MINIO_TEST_SECRET_KEY", "minioadmin")

pytestmark = pytest.mark.skipif(
    not ENDPOINT,
    reason="set MINIO_TEST_ENDPOINT to run live MinIO integration tests",
)

# NOTE(abi): we set a value comfortably above the 8 MB multipart threshold,
#            to ensure the transfer is chunked.
_LARGE_SIZE = 12 * 1024 * 1024


@pytest.fixture
def client():
    """Fixture of a client pointed at the live MinIO server, with a unique scratch bucket."""
    c = cast(
        S3Backend,
        get_client(
            "minio",
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            endpoint_url=ENDPOINT,
            region="us-east-1",
        ),
    )
    bucket = f"anybucket-it-{uuid.uuid4().hex[:12]}"
    c.ensure_bucket(bucket)

    try:
        yield c, bucket
    finally:
        # Empty then remove the bucket via the underlying boto3 client.
        for key in c.list_keys(bucket):
            c._client.delete_object(Bucket=bucket, Key=key)

        c._client.delete_bucket(Bucket=bucket)


def test_multipart_roundtrip_against_real_server(client, tmp_path):
    """Test that a file above the multipart threshold round-trips byte-for-byte."""
    c, bucket = client

    src = tmp_path / "big.bin"
    payload = os.urandom(_LARGE_SIZE)
    src.write_bytes(payload)

    up = c.upload(src, bucket, prefix="large/")
    assert up.success
    assert up.key == "large/big.bin"

    assert c.exists(bucket, "large/big.bin")
    assert c.list_keys(bucket) == ["large/big.bin"]

    dst = tmp_path / "out" / "big.bin"
    down = c.download(bucket, "large/big.bin", dst)
    assert down.success
    assert dst.read_bytes() == payload


def test_uri_convenience_against_real_server(client, tmp_path):
    """Test that ``put``/``get`` work against a real server using ``s3://`` URIs."""
    c, bucket = client

    src = tmp_path / "scene.tif"
    src.write_bytes(b"\x00" * 2048)

    assert c.put(src, f"s3://{bucket}/2026/scene.tif").success
    assert c.exists(bucket, "2026/scene.tif")

    dst = tmp_path / "scene.tif"
    assert c.get(f"s3://{bucket}/2026/scene.tif", dst).success
    assert dst.read_bytes() == b"\x00" * 2048
