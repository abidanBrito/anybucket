"""
Tests for ``S3Config.resolve``.

Cover explicit values winning over the environent ones, the environment
variables fallbacks, custom prefixes, and the missing-credential
error.
"""

import pytest

from anybucket import S3Config
from anybucket.exceptions import ConfigError


def test_explicit_args_win(monkeypatch):
    """Explicit arguments take precedence over environment variables."""
    monkeypatch.setenv("STORAGE_ACCESS_KEY", "from-env")
    cfg = S3Config.resolve(access_key="explicit", secret_key="s")
    assert cfg.access_key == "explicit"
    assert cfg.secret_key == "s"
    assert cfg.region == "us-east-1"


def test_env_fallback(monkeypatch):
    """Unset arguments fall back to the matching environment variables."""
    monkeypatch.setenv("STORAGE_ACCESS_KEY", "ak")
    monkeypatch.setenv("STORAGE_SECRET_KEY", "sk")
    monkeypatch.setenv("STORAGE_ENDPOINT_URL", "http://minio:9000")
    cfg = S3Config.resolve()
    assert (cfg.access_key, cfg.secret_key) == ("ak", "sk")
    assert cfg.endpoint_url == "http://minio:9000"


def test_custom_prefix(monkeypatch):
    """A custom ``env_prefix`` reads from the matching variables."""
    monkeypatch.setenv("MINIO_ACCESS_KEY", "ak")
    monkeypatch.setenv("MINIO_SECRET_KEY", "sk")
    cfg = S3Config.resolve(env_prefix="MINIO_")
    assert cfg.access_key == "ak"


def test_missing_credentials_raise(monkeypatch):
    """Absent credentials raise ``ConfigError``."""
    monkeypatch.delenv("STORAGE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("STORAGE_SECRET_KEY", raising=False)
    with pytest.raises(ConfigError):
        S3Config.resolve()
