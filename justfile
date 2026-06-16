# justfile

_default:
    @just --list

# Install/update dev environment
sync:
    uv sync

# Auto-format codebase
format:
    uv run ruff format

# Lint codebase
lint:
    uv run ruff check

# Auto-fix lint issues
fix:
    uv run ruff check --fix

# Type-check cobebase
type:
    uv run pyrefly check

# Lint, type-check and run tests
check: lint type test

# Run test suite
test:
    uv run pytest

# Install pre-commit hooks (on push, not commit)
hooks:
    uv run pre-commit install --hook-type pre-push

# Build wheel + sdist
build:
    uv build

# Integration test against a throwaway MinIO container (needs Docker)
minio-test:
    #!/usr/bin/env bash

    set -euo pipefail

    name="anybucket-minio-it"
    docker rm -f "$name" >/dev/null 2>&1 || true
    docker run -d --rm --name "$name" -p 9000:9000 \
        -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
        minio/minio server /data >/dev/null

    cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
    trap cleanup EXIT

    echo "Waiting for MinIO to accept connections..."
    for _ in $(seq 1 30); do
        curl -sf http://localhost:9000/minio/health/live >/dev/null && break
        sleep 1
    done

    MINIO_TEST_ENDPOINT=http://localhost:9000 \
        uv run pytest tests/test_minio_integration.py -v
