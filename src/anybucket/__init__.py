"""
Top-level package for the anybucket library.

Provides a unified interface over object-storage buckets.
"""

__version__ = "0.0.1"

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tesserae")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__author__ = "Abidán Brito <abidan.brito@gmail.com>"
__copyright__ = "Copyright 2026, Abidán Brito"

__all__ = []
