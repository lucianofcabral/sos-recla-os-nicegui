"""Database engine and session helpers."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DATABASE_URL = 'sqlite:///sos.db'


def load_env() -> None:
    """Load variables from the project ``.env`` file when present.

    ``load_dotenv`` does not override variables already set in the
    environment, so explicit exports always win.
    """
    load_dotenv()


def get_database_url() -> str:
    """Return the configured database URL, falling back to SQLite in dev."""
    load_env()
    return os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL)


def build_engine(database_url: str | None = None) -> Engine:
    """Build an engine for the given URL (or the configured one)."""
    url = database_url or get_database_url()
    connect_args = {'check_same_thread': False} if url.startswith('sqlite') else {}
    return create_engine(url, connect_args=connect_args)


def create_schema(engine: Engine) -> None:
    """Create all tables defined by the SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a sessionmaker bound to the given engine."""
    return sessionmaker(
        bind=engine, class_=Session, autoflush=False, expire_on_commit=False
    )
