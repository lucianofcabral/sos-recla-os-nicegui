import bcrypt

from src.domain.domain_enums import RoleEnum
from src.domain.dto.create import UserCreate
from src.domain.exceptions import DomainError
from src.domain.models.entities import User
from src.domain.ports.unit_of_work import UnitOfWorkPort


class CrearUsuario:
    """Create a new user; only ADMIN callers are allowed (password is bcrypt-hashed)."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, data: UserCreate, *, actor: User) -> User:
        with self._uow:
            if actor.role != RoleEnum.ADMIN:
                raise DomainError('solo un administrador puede crear usuarios')
            password_hash = bcrypt.hashpw(
                data.password.encode('utf-8'), bcrypt.gensalt()
            ).decode('utf-8')
            user = User(
                username=data.username,
                password_hash=password_hash,
                role=data.role or RoleEnum.USER,
                active=True,
            )
            user = self._uow.users.save(user)
            self._uow.commit()
            return user


class AutenticarUsuario:
    """Validate username/password and return the active user."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    def __call__(self, username: str, password: str) -> User:
        with self._uow:
            user = self._uow.users.get_by_username(username)
            if user is None or not user.active:
                raise DomainError('usuario o contraseña inválidos')
            if not bcrypt.checkpw(
                password.encode('utf-8'), user.password_hash.encode('utf-8')
            ):
                raise DomainError('usuario o contraseña inválidos')
            self._uow.commit()
            return user
