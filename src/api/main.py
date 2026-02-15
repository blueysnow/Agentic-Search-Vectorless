"""Main entry point for uvicorn."""

from src.api.server import create_app

app = create_app()
