"""
The single entry point: ``get_client(provider, ...)``.

Most labels are S3-compatible and share :class:`S3Backend`; ``gcs`` uses the
native :class:`GCSBackend`.
"""

from __future__ import annotations

from enum import StrEnum

from .backends import S3Backend
from .base import StorageBackend
from .config import DEFAULT_ENV_PREFIX, GCSConfig, S3Config
from .exceptions import ProviderError


class Provider(StrEnum):
    """Known provider labels."""

    S3 = "s3"
    AWS = "aws"
    MINIO = "minio"
    OVH = "ovh"
    R2 = "r2"
    B2 = "b2"
    CEPH = "ceph"
    GCS = "gcs"


_KNOWN_PROVIDERS = frozenset(p.value for p in Provider)


def get_client(
    provider: str | Provider = Provider.MINIO,
    *,
    access_key: str | None = None,
    secret_key: str | None = None,
    endpoint_url: str | None = None,
    region: str | None = None,
    project: str | None = None,
    credentials_path: str | None = None,
    env_prefix: str = DEFAULT_ENV_PREFIX,
    transfer_config=None,
) -> StorageBackend:
    """
    Create a configured storage client.

    Settings are taken from the explicit arguments, falling back to
    ``{env_prefix}*`` environment variables for anything left as ``None``
    (see :meth:`S3Config.resolve` / :meth:`GCSConfig.resolve`).

    :param provider: which backend to use. Defaults to ``"minio"``. Unknown
        values raise :class:`ProviderError`.
    :param access_key: explicit access key (S3); falls back to the environment.
    :param secret_key: explicit secret key (S3); falls back to the environment.
    :param endpoint_url: explicit endpoint URL (S3); falls back to the environment.
    :param region: explicit region (S3); falls back to the environment.
    :param project: explicit GCP project (GCS); falls back to the environment.
    :param credentials_path: service-account JSON path (GCS); falls back to the
        environment, then to Application Default Credentials.
    :param env_prefix: prefix for the environment-variable fallback
        (default ``"STORAGE_"``).
    :param transfer_config: optional boto3 ``TransferConfig`` passed through to
        S3-compatible backends.
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
    if key not in _KNOWN_PROVIDERS:
        known = ", ".join(sorted(_KNOWN_PROVIDERS))
        raise ProviderError(f"Unknown provider {provider!r}. Known: {known}.")

    if key == Provider.GCS.value:
        from .backends.gcs import GCSBackend

        gcs_config = GCSConfig.resolve(
            project=project,
            credentials_path=credentials_path,
            env_prefix=env_prefix,
        )

        return GCSBackend(gcs_config)

    config = S3Config.resolve(
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url,
        region=region,
        env_prefix=env_prefix,
    )

    return S3Backend(config, transfer_config=transfer_config)
