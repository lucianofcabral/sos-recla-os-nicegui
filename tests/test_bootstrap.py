"""Tests for the bootstrap first-user helper."""

from __future__ import annotations

import bcrypt
import pytest

from scripts.bootstrap import create_first_user, main
from src.domain.domain_enums import RoleEnum
from src.domain.exceptions import DomainError, DuplicateEntityError
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_create_first_user_hashes_password() -> None:
    with FakeUnitOfWork() as uow:
        user = create_first_user(uow, 'boss', 'secret123', role=RoleEnum.ADMIN)
        assert uow.committed is True
        assert user.username == 'boss'
        assert user.role == RoleEnum.ADMIN
        assert user.active is True
        assert user.password_hash != 'secret123'
        assert bcrypt.checkpw(b'secret123', user.password_hash.encode('utf-8'))
        assert uow.users.get_by_username('boss') is not None


def test_create_first_user_default_role_is_admin() -> None:
    with FakeUnitOfWork() as uow:
        user = create_first_user(uow, 'boss', 'secret123')
        assert user.role == RoleEnum.ADMIN


def test_create_first_user_duplicate_raises() -> None:
    with FakeUnitOfWork() as uow:
        create_first_user(uow, 'boss', 'secret123')
        with pytest.raises(DuplicateEntityError):
            create_first_user(uow, 'boss', 'otherpass')


def test_create_first_user_short_password_raises() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(DomainError):
        create_first_user(uow, 'boss', 'short')


def test_main_returns_error_for_short_password() -> None:
    assert main(['--username', 'boss', '--password', 'short']) == 1
