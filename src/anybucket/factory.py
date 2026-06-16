"""
The single entry point: ``get_client(provider, ...)``.

Adding a new provider is a two-line change here: register an alias in
``_REGISTRY`` and point it at a new builder (for a non-S3 backend).
"""

from __future__ import annotations

from enum import StrEnum
from typing import cast

from .backends import S3Backend
from .base import StorageBackend
from .config import DEFAULT_ENV_PREFIX, S3Config
from .exceptions import ProviderError


class Provider(StrEnum):
    """Known provider labels. All current values are S3-compatible."""

    S3 = "s3"
    AWS = "aws"
    MINIO = "minio"
    OVH = "ovh"
    R2 = "r2"
    B2 = "b2"
    CEPH = "ceph"


# Provider label -> backend class
# NOTE(abi): several labels intentionally share the same backend (e.g. S3Backend).
_REGISTRY: dict[str, type[StorageBackend]] = {p.value: S3Backend for p in Provider}


def get_client(
    provider: str | Provider = Provider.MINIO,
    *,
    access_key: str | None = None,
    secret_key: str | None = None,
    endpoint_url: str | None = None,
    region: str | None = None,
    env_prefix: str = DEFAULT_ENV_PREFIX,
    transfer_config=None,
) -> StorageBackend:
    """
    Create a configured storage client.

    Credentials are taken from the explicit arguments, falling back to
    ``{env_prefix}*`` environment variables for anything left as ``None``
    (see :meth:`S3Config.resolve`).

    :param provider: which backend to use. Defaults to ``"minio"``. Unknown
        values raise :class:`ProviderError`.
    :param access_key: explicit access key; falls back to the environment.
    :param secret_key: explicit secret key; falls back to the environment.
    :param endpoint_url: explicit endpoint URL; falls back to the environment.
    :param region: explicit region; falls back to the environment.
    :param env_prefix: prefix for the environment-variable fallback
        (default ``"STORAGE_"``).
    :param transfer_config: optional boto3 ``TransferConfig`` passed through to
        the backend.
    :returns: a configured storage client.
    :raises ProviderError: if ``provider`` is not a known label.

    .. rubric:: Example

    >>> client = get_client(
    ...     "minio",
    ...     access_key="minioadmin",
    ...     secret_key="minioadmin",
    ...     endpoint_url="http://localhost:9000",
    ... )
    >>> client.put("ndvi.tif", "s3://rasters/2026/ndvi.tif")
    """
    key = provider.value if isinstance(provider, Provider) else str(provider).lower()
    backend_cls = _REGISTRY.get(key)
    if backend_cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ProviderError(f"Unknown provider {provider!r}. Known: {known}.")

    config = S3Config.resolve(
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url,
        region=region,
        env_prefix=env_prefix,
    )

    return cast(type[S3Backend], backend_cls)(config, transfer_config=transfer_config)
