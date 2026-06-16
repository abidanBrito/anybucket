"""
Tests for the public package surface.

Verify the top-level package imports cleanly and properly exposes
every advertised name.
"""

import anybucket


def test_version_is_exposed():
    """The package exposes a version string."""
    assert isinstance(anybucket.__version__, str)


def test_all_exports_are_importable():
    """Every name listed in ``__all__`` is accessible on the package."""
    for name in anybucket.__all__:
        assert hasattr(anybucket, name), f"{name!r} is in __all__ but not importable"
