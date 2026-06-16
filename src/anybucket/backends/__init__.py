"""
Backends package.

Provides concrete storage backend implementations.
"""

from .s3 import S3Backend

__all__ = ["S3Backend"]
