"""
Round-trip tests against a mocked S3 service.

These cover library *logic* against an S3 API emulator. For verification
against a real S3 server, see ``test_minio_integration.py``.
"""

from typing import cast

import pytest

moto = pytest.importorskip("moto")

from anybucket import S3Backend, get_client  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    """Define a fixture for a backend bound to a mocked S3 service with a ready ``bucket``."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with moto.mock_aws():
        c = cast(
            S3Backend,
            get_client("s3", access_key="testing", secret_key="testing", region="us-east-1"),
        )
        c.ensure_bucket("bucket")
        yield c


def test_upload_download_roundtrip(client, tmp_path):
    """Test that a file uploaded under a prefix downloads back identically."""
    src = tmp_path / "hello.txt"
    src.write_text("hello world")

    up = client.upload(src, "bucket", prefix="docs/")
    assert up.success
    assert up.key == "docs/hello.txt"
    assert up.uri == "s3://bucket/docs/hello.txt"

    assert client.exists("bucket", "docs/hello.txt")
    assert client.list_keys("bucket") == ["docs/hello.txt"]

    dst = tmp_path / "out" / "hello.txt"
    down = client.download("bucket", "docs/hello.txt", dst)
    assert down.success
    assert dst.read_text() == "hello world"


def test_uri_convenience(client, tmp_path):
    """Test ``put``/``get`` address objects with a single ``s3://`` URI."""
    src = tmp_path / "scene.tif"
    src.write_bytes(b"\x00" * 1024)

    assert client.put(src, "s3://bucket/2026/scene.tif").success
    assert client.exists("bucket", "2026/scene.tif")

    dst = tmp_path / "scene.tif"
    assert client.get("s3://bucket/2026/scene.tif", dst).success
    assert dst.read_bytes() == b"\x00" * 1024


def test_upload_missing_file_returns_failure(client, tmp_path):
    """Test that uploading a missing file returns a failure result instead of raising."""
    res = client.upload(tmp_path / "nope.txt", "bucket")
    assert not res.success
    assert "Not a file" in res.message


def test_delete_after_upload(client, tmp_path):
    """Test that ``delete_after`` removes the local file once the upload succeeds."""
    src = tmp_path / "tmp.txt"
    src.write_text("x")
    assert client.upload(src, "bucket", delete_after=True).success
    assert not src.exists()
