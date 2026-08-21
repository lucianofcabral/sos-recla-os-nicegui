"""Shared UI helpers: per-request unit of work and session auth helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nicegui import app, ui
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from src.domain.domain_enums import RoleEnum
from src.domain.models.entities import User
from src.infrastructure.database import build_engine, session_factory
from src.infrastructure.unit_of_work import SqlModelUnitOfWork

CURRENT_USER_KEY = 'current_user'
THEME_KEY = 'theme'

ADMIN_ROLES: tuple[RoleEnum, ...] = (RoleEnum.ADMIN,)

_sessionmaker: sessionmaker[Session] | None = None


def _get_session_factory() -> sessionmaker[Session]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = session_factory(build_engine())
    return _sessionmaker


@contextmanager
def uow_per_request() -> Iterator[SqlModelUnitOfWork]:
    """Yield a real unit of work backed by a fresh session for one request."""
    session = _get_session_factory()()
    try:
        yield SqlModelUnitOfWork(session)
    finally:
        session.close()


def get_current_user() -> User | None:
    """Return the logged-in user stored in the session, or None.

    The user is persisted as a JSON-serializable dict (via model_dump(mode='json'))
    because NiceGUI's storage requires JSON-compatible values. Older sessions may
    still hold a raw User object in memory, so we tolerate that shape too.
    """
    data = app.storage.user.get(CURRENT_USER_KEY)
    if data is None:
        return None
    if isinstance(data, User):
        return data
    return User.model_validate(data)


def require_login() -> User | None:
    """Return the current user; queue a redirect to /login when not logged in."""
    user = get_current_user()
    if user is None:
        ui.navigate.to('/login')
    return user


def current_user_id() -> int | None:
    """Return the id of the logged-in user, or None."""
    user = get_current_user()
    return user.id if user is not None else None


def is_admin(user: User | None) -> bool:
    """Return True when the given user has an admin role."""
    return user is not None and user.role in ADMIN_ROLES
