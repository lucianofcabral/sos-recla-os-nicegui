import bcrypt
import pytest
from pydantic import ValidationError

from src.application.use_cases.register_user import AutenticarUsuario, CrearUsuario
from src.domain.domain_enums import RoleEnum
from src.domain.dto.create import UserCreate
from src.domain.exceptions import DomainError, DuplicateEntityError
from src.domain.models.entities import User
from tests.fakes.unit_of_work import FakeUnitOfWork


def _admin() -> User:
    return User(
        id=1,
        username='admin',
        password_hash='not-a-real-hash',
        role=RoleEnum.ADMIN,
        active=True,
    )


def _regular_user() -> User:
    return User(
        id=2,
        username='regular',
        password_hash='not-a-real-hash',
        role=RoleEnum.USER,
        active=True,
    )


def test_admin_creates_user_with_hashed_password() -> None:
    with FakeUnitOfWork() as uow:
        created = CrearUsuario(uow)(
            UserCreate(username='admin2', password='secret123', role=RoleEnum.ADMIN),
            actor=_admin(),
        )
        assert uow.committed is True
        assert created.id is not None
        assert created.password_hash != 'secret123'
        assert bcrypt.checkpw(b'secret123', created.password_hash.encode('utf-8'))
        assert created.role == RoleEnum.ADMIN
        assert created.active is True


def test_non_admin_cannot_create_user() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(DomainError):
        CrearUsuario(uow)(
            UserCreate(username='foo', password='secret123'), actor=_regular_user()
        )


def test_duplicate_username_raises() -> None:
    with FakeUnitOfWork() as uow:
        use_case = CrearUsuario(uow)
        use_case(UserCreate(username='dupe', password='secret123'), actor=_admin())
        with pytest.raises(DuplicateEntityError):
            use_case(UserCreate(username='dupe', password='secret456'), actor=_admin())


def test_short_password_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username='x', password='short')


def test_autenticar_ok_returns_active_user() -> None:
    with FakeUnitOfWork() as uow:
        CrearUsuario(uow)(
            UserCreate(username='carlos', password='secret123'), actor=_admin()
        )
        user = AutenticarUsuario(uow)(username='carlos', password='secret123')
        assert user.username == 'carlos'
        assert user.active is True


def test_autenticar_wrong_password_raises() -> None:
    uow = FakeUnitOfWork()
    CrearUsuario(uow)(
        UserCreate(username='carlos', password='secret123'), actor=_admin()
    )
    with pytest.raises(DomainError):
        AutenticarUsuario(uow)(username='carlos', password='wrongpass')


def test_autenticar_unknown_user_raises() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(DomainError):
        AutenticarUsuario(uow)(username='ghost', password='secret123')


def test_autenticar_inactive_user_raises() -> None:
    uow = FakeUnitOfWork()
    password_hash = bcrypt.hashpw(b'secret123', bcrypt.gensalt()).decode('utf-8')
    uow.users.save(User(username='ghost', password_hash=password_hash, active=False))
    with pytest.raises(DomainError):
        AutenticarUsuario(uow)(username='ghost', password='secret123')
