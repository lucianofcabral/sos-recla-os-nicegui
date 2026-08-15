"""CLI to create the very first system user (bootstrap).

The first user cannot be created through CrearUsuario because there is no
admin actor yet, so this helper writes the hashed user directly through the
unit of work. It exists ONLY for the bootstrap flow.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bcrypt
from sqlmodel import Session

from src.domain.domain_enums import RoleEnum
from src.domain.exceptions import DomainError, DuplicateEntityError
from src.domain.models.entities import User
from src.domain.ports.unit_of_work import UnitOfWorkPort
from src.infrastructure.database import build_engine, create_schema, load_env
from src.infrastructure.unit_of_work import SqlModelUnitOfWork

MIN_PASSWORD_LENGTH = 8

ROLE_FLAGS: dict[str, RoleEnum] = {'admin': RoleEnum.ADMIN, 'user': RoleEnum.USER}


def create_first_user(
    uow: UnitOfWorkPort,
    username: str,
    password: str,
    role: RoleEnum = RoleEnum.ADMIN,
) -> User:
    """Create the first user directly, hashing the password with bcrypt."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(
            f'La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres'
        )
    if uow.users.get_by_username(username) is not None:
        raise DuplicateEntityError(
            f'El usuario {username!r} ya existe. No se sobrescribe la contraseña.'
        )
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode(
        'utf-8'
    )
    user = User(username=username, password_hash=password_hash, role=role, active=True)
    with uow:
        user = uow.users.save(user)
        uow.commit()
    return user


def main(argv: Sequence[str] | None = None) -> int:
    load_env()  # bootstrap reads BOOTSTRAP_* vars from the project .env
    parser = argparse.ArgumentParser(
        description='Crear el primer usuario del sistema SOS Reclamos.'
    )
    parser.add_argument(
        '--username',
        default=os.getenv('BOOTSTRAP_USER'),
        help='Nombre de usuario (o variable de entorno BOOTSTRAP_USER).',
    )
    parser.add_argument(
        '--password',
        default=os.getenv('BOOTSTRAP_PASSWORD'),
        help=f'Contraseña (mínimo {MIN_PASSWORD_LENGTH} caracteres, o variable '
        'de entorno BOOTSTRAP_PASSWORD).',
    )
    parser.add_argument(
        '--role',
        default=os.getenv('BOOTSTRAP_ROLE', 'admin'),
        choices=ROLE_FLAGS,
        help='Rol del usuario (admin o user).',
    )
    args = parser.parse_args(argv)
    if not args.username:
        parser.error('--username es obligatorio (o definir BOOTSTRAP_USER)')
    if not args.password:
        parser.error('--password es obligatorio (o definir BOOTSTRAP_PASSWORD)')
    role = ROLE_FLAGS[args.role]
    engine = build_engine()
    create_schema(engine)
    with Session(engine) as session:
        try:
            create_first_user(
                SqlModelUnitOfWork(session), args.username, args.password, role=role
            )
        except DomainError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
    print('Primer usuario creado correctamente.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
