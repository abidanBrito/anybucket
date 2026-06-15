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
