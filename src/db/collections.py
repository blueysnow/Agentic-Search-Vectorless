"""Typed collection accessors for the five core collections."""

from __future__ import annotations

from pymongo.collection import Collection

from src.db.client import get_database

# Collection name constants
DOCUMENTS = "documents"
NODES = "nodes"
PAGES = "pages"
RETRIEVAL_SESSIONS = "retrieval_sessions"
ANALYTICS = "analytics"


def documents_col() -> Collection:
    return get_database()[DOCUMENTS]


def nodes_col() -> Collection:
    return get_database()[NODES]


def pages_col() -> Collection:
    return get_database()[PAGES]


def retrieval_sessions_col() -> Collection:
    return get_database()[RETRIEVAL_SESSIONS]


def analytics_col() -> Collection:
    return get_database()[ANALYTICS]
