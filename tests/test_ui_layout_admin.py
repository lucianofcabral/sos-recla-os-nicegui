"""Unit tests for the ADMIN-only nav entry and page gate."""

from __future__ import annotations

import pytest

from src.domain.domain_enums import RoleEnum
from src.domain.models.entities import User

pytestmark = pytest.mark.usefixtures('monkeypatch')


def _user(role: RoleEnum) -> User:
    return User(username=role.value.lower(), password_hash='x', role=role)


def test_nav_items_migracion_is_admin_only() -> None:
    from src.ui.layout import NAV_ITEMS

    migracion = next(item for item in NAV_ITEMS if item.path == '/migracion')
    assert migracion.title == 'Migración'
    assert migracion.icon == 'upload_file'
    assert migracion.admin_only is True


def test_page_admin_only_blocks_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.ui.layout as layout

    calls: dict[str, list] = {'notify': [], 'navigate': [], 'shell': [], 'build': []}
    monkeypatch.setattr(
        layout.ui,
        'notify',
        lambda *args, **kwargs: calls['notify'].append((args, kwargs)),
    )
    monkeypatch.setattr(
        layout.ui.navigate, 'to', lambda *args, **kwargs: calls['navigate'].append(args)
    )
    monkeypatch.setattr(layout, 'require_login', lambda: _user(RoleEnum.USER))
    monkeypatch.setattr(
        layout, 'render_shell', lambda *a, **k: calls['shell'].append(a)
    )
    monkeypatch.setattr(layout.ui, 'page', lambda path: lambda fn: fn)

    @layout.page('X', path='/admin-test', admin_only=True)
    def build(user: User) -> None:
        calls['build'].append(user)

    build()

    assert calls['notify'] == [(('No autorizado',), {'type': 'negative'})]
    assert calls['navigate'] == [('/',)]
    assert calls['shell'] == []
    assert calls['build'] == []


def test_page_admin_only_allows_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.ui.layout as layout

    calls: dict[str, list] = {'shell': [], 'build': []}
    monkeypatch.setattr(layout, 'require_login', lambda: _user(RoleEnum.ADMIN))
    monkeypatch.setattr(
        layout, 'render_shell', lambda *a, **k: calls['shell'].append(a)
    )
    monkeypatch.setattr(layout.ui, 'page', lambda path: lambda fn: fn)

    @layout.page('X', path='/admin-test-2', admin_only=True)
    def build(user: User) -> None:
        calls['build'].append(user)

    build()

    assert len(calls['shell']) == 1
    assert len(calls['build']) == 1
    assert calls['build'][0].role == RoleEnum.ADMIN
