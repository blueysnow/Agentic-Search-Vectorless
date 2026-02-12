"""MongoDB client singleton (pymongo synchronous driver)."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from src.config import get_settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return (and lazily create) the singleton MongoClient."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(
            settings.mongodb_uri,
            maxPoolSize=50,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
        )
    return _client


def get_database() -> Database:
    """Return the application database handle."""
    settings = get_settings()
    return get_client()[settings.mongodb_database]


def ping() -> bool:
    """Verify the MongoDB connection is alive.

    Returns True on success, raises ConnectionFailure on failure.
    """
    try:
        get_client().admin.command("ping")
        return True
    except ConnectionFailure:
        raise
    except Exception as exc:
        raise ConnectionFailure(f"MongoDB ping failed: {exc}") from exc


def close_client() -> None:
    """Close the MongoClient and reset the singleton."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
