"""Shared page shell: login gate, header with nav, theme toggle and logout."""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from nicegui import app, ui

from src.domain.models.entities import User
from src.ui.deps import THEME_KEY, is_admin, require_login


class NavItem(NamedTuple):
    """Header navigation entry: title, path, icon and admin-only flag."""

    title: str
    path: str
    icon: str
    admin_only: bool = False


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem('Inicio', '/', 'home'),
    NavItem('Pagos', '/pagos', 'payments'),
    NavItem('Ciclos', '/ciclos', 'date_range'),
    NavItem('Migración', '/migracion', 'upload_file', admin_only=True),
)


def render_shell(title: str, user: User) -> None:
    """Apply the user preferences and render the shared application header."""
    dark_mode = ui.dark_mode(bool(app.storage.user.get(THEME_KEY, True)))

    def toggle_theme() -> None:
        new_value = not bool(app.storage.user.get(THEME_KEY, True))
        app.storage.user[THEME_KEY] = new_value
        dark_mode.set_value(new_value)

    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to('/login')

    with (
        ui.header().classes('bg-primary text-white').props('elevated'),
        ui.row().classes('items-center w-full q-px-md'),
    ):
        ui.icon('support_agent').classes('text-h4')
        ui.label('SOS Reclamos').classes('text-h6 q-ml-sm text-weight-medium')
        with ui.tabs(value=title).classes('text-white q-ml-lg'):
            for nav_item in NAV_ITEMS:
                if nav_item.admin_only and not is_admin(user):
                    continue
                tab = ui.tab(nav_item.title, icon=nav_item.icon)
                tab.on('click', lambda p=nav_item.path: ui.navigate.to(p))
        ui.space()
        theme_button = ui.button(icon='dark_mode').props('flat round text-white')
        theme_button.tooltip('Cambiar a tema claro/oscuro')
        theme_button.on('click', toggle_theme)
        logout_button = ui.button('Cerrar Sesión', icon='logout').props(
            'flat text-white'
        )
        logout_button.tooltip('Cerrar la sesión actual')
        logout_button.on('click', logout)


def page(title: str, path: str = '/', admin_only: bool = False):
    """Decorate a content builder with login and role enforcement plus the shell."""

    def decorator(build: Callable[[User], None]):
        @ui.page(path)
        def wrapper() -> None:
            user = require_login()
            if user is None:
                return
            if admin_only and not is_admin(user):
                ui.notify('No autorizado', type='negative')
                ui.navigate.to('/')
                return
            render_shell(title, user)
            build(user)

        return wrapper

    return decorator
