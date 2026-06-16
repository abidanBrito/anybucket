"""
Connection settings and explicit-args-with-env-fallback resolution.

The factory accepts credentials explicitly, but any value left as ``None`` is
filled from the environment. With the default ``env_prefix="STORAGE_"`` the
variables are:

    STORAGE_ACCESS_KEY
    STORAGE_SECRET_KEY
    STORAGE_ENDPOINT_URL
    STORAGE_REGION

Pass a different prefix (e.g. ``"MINIO_"``) to read a provider-specific set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .exceptions import ConfigError

DEFAULT_ENV_PREFIX = "STORAGE_"
_DEFAULT_REGION = "us-east-1"


@dataclass(frozen=True)
class S3Config:
    """
    Everything needed to open a connection to an S3-compatible provider.

    :ivar access_key: access-key credential (``AWS_ACCESS_KEY_ID`` equivalent).
    :ivar secret_key: secret-key credential (``AWS_SECRET_ACCESS_KEY`` equivalent).
    :ivar endpoint_url: full provider URL, e.g. ``http://minio:9000``;
        ``None`` targets real AWS S3.
    :ivar region: region name. Required by AWS S3, ignored by most other providers.
    """

    access_key: str
    secret_key: str
    endpoint_url: str | None = None
    region: str = _DEFAULT_REGION

    @classmethod
    def resolve(
        cls,
        *,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        region: str | None = None,
        env_prefix: str = DEFAULT_ENV_PREFIX,
    ) -> S3Config:
        """
        Build a config from explicit values, falling back to the environment.

        Any argument left ``None`` is read from ``{env_prefix}<NAME>``.

        :param access_key: access-key credential, or ``None`` to read from the env.
        :param secret_key: secret-key credential, or ``None`` to read from the env.
        :param endpoint_url: provider URL, or ``None`` to read from the env.
        :param region: region name, or ``None`` to read from the env.
        :param env_prefix: prefix for the environment-variable fallback.
        :returns: a frozen config instance.
        :raises ConfigError: if credentials cannot be found explicitly or in the env.
        """
        access_key = access_key or os.environ.get(f"{env_prefix}ACCESS_KEY")
        secret_key = secret_key or os.environ.get(f"{env_prefix}SECRET_KEY")
        endpoint_url = endpoint_url or os.environ.get(f"{env_prefix}ENDPOINT_URL")
        region = region or os.environ.get(f"{env_prefix}REGION") or _DEFAULT_REGION

        missing = [
            name
            for name, value in (("access_key", access_key), ("secret_key", secret_key))
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing required credential(s): "
                + ", ".join(missing)
                + f". Pass them explicitly or set {env_prefix}ACCESS_KEY / "
                f"{env_prefix}SECRET_KEY in the environment."
            )

        assert access_key is not None
        assert secret_key is not None

        return cls(
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            region=region,
        )
