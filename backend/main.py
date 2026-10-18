"""Convenience ASGI entrypoint: uv run uvicorn main:app --host 127.0.0.1."""

from faultline_backend.app import app

__all__ = ["app"]
