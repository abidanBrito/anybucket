"""Smoke tests for the anybucket package."""

import anybucket


def test_version_is_exposed():
    """Test that the package version gets exposed."""
    assert isinstance(anybucket.__version__, str)
