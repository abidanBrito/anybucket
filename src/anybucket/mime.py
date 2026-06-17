"""
Content-type inference shared across backends.

Provider-agnostic (stdlib only) so that every backend can reuse it without
pulling in another backend's SDK.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

# Geospatial/scientific data content types mimetypes doesn't know about
_EXTRA_CONTENT_TYPES = {
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".jp2": "image/jp2",
    ".hdf": "application/x-hdf",
    ".h5": "application/x-hdf5",
    ".nc": "application/x-netcdf",
}


def infer_content_type(path: Path) -> str:
    """Return a best-effort MIME type for ``path`` (octet-stream if unknown)."""
    mime, _ = mimetypes.guess_type(path.name)
    if mime:
        return mime

    return _EXTRA_CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
