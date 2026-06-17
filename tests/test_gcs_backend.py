"""
Round-trip tests against an in-memory fake GCS client.

These cover library *logic* against a stand-in for ``google-cloud-storage``.
"""

from typing import cast

import pytest

pytest.importorskip("google.cloud.storage")

from google.api_core.exceptions import NotFound  # noqa: E402

from anybucket import GCSBackend, get_client  # noqa: E402


class _FakeBlob:
    """A single object backed by a shared in-memory ``store`` dict."""

    def __init__(self, store: dict, bucket: str, name: str) -> None:
        self._store = store
        self._bucket = bucket
        self.name = name
        self.metadata: dict | None = None

    def upload_from_filename(self, filename: str, content_type: str | None = None) -> None:
        self._store[(self._bucket, self.name)] = (content_type, open(filename, "rb").read())

    def download_to_filename(self, filename: str) -> None:
        entry = self._store.get((self._bucket, self.name))
        if entry is None:
            raise NotFound(f"gs://{self._bucket}/{self.name}")

        with open(filename, "wb") as fh:
            fh.write(entry[1])

    def exists(self) -> bool:
        return (self._bucket, self.name) in self._store


class _FakeBucket:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self.name = name

    def blob(self, key: str) -> _FakeBlob:
        return _FakeBlob(self._store, self.name, key)

    def exists(self) -> bool:
        return True


class _FakeClient:
    """Minimal stand-in for ``google.cloud.storage.Client``."""

    def __init__(self, *args, **kwargs) -> None:
        self._store: dict = {}

    def bucket(self, name: str) -> _FakeBucket:
        return _FakeBucket(self._store, name)

    def list_blobs(self, bucket: str, prefix: str = ""):
        return [
            _FakeBlob(self._store, b, name)
            for (b, name) in self._store
            if b == bucket and name.startswith(prefix)
        ]

    def create_bucket(self, name: str) -> None:
        pass


@pytest.fixture
def client(monkeypatch):
    """Define a fixture for a backend bound to an in-memory fake GCS client."""
    monkeypatch.setattr("anybucket.backends.gcs.storage.Client", _FakeClient)
    return cast(GCSBackend, get_client("gcs"))


def test_upload_download_roundtrip(client, tmp_path):
    """Test that a file uploaded under a prefix downloads back identically."""
    src = tmp_path / "hello.txt"
    src.write_text("hello world")

    up = client.upload(src, "bucket", prefix="docs/")
    assert up.success
    assert up.key == "docs/hello.txt"

    assert client.exists("bucket", "docs/hello.txt")
    assert client.list_keys("bucket") == ["docs/hello.txt"]

    dst = tmp_path / "out" / "hello.txt"
    down = client.download("bucket", "docs/hello.txt", dst)
    assert down.success
    assert dst.read_text() == "hello world"


def test_uri_convenience(client, tmp_path):
    """Test ``put``/``get`` address objects with a single URI."""
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


def test_download_missing_object_returns_failure(client, tmp_path):
    """Test that downloading a missing object returns a failure result instead of raising."""
    res = client.download("bucket", "nope.txt", tmp_path / "nope.txt")
    assert not res.success


def test_delete_after_upload(client, tmp_path):
    """Test that ``delete_after`` removes the local file once the upload succeeds."""
    src = tmp_path / "tmp.txt"
    src.write_text("x")
    assert client.upload(src, "bucket", delete_after=True).success
    assert not src.exists()
