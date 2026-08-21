"""Login page: authenticate with username and password."""

from __future__ import annotations

from nicegui import app, ui

from src.application.use_cases.register_user import AutenticarUsuario
from src.domain.exceptions import DomainError
from src.ui.deps import CURRENT_USER_KEY, get_current_user, uow_per_request
from src.ui.theme import apply_theme

INVALID_CREDENTIALS = 'usuario o contraseña inválidos'


def _try_login(username: str, password: str) -> bool:
    try:
        with uow_per_request() as uow:
            user = AutenticarUsuario(uow)(username, password)
    except DomainError:
        ui.notify(INVALID_CREDENTIALS, type='negative', close_button=True)
        return False
    app.storage.user[CURRENT_USER_KEY] = user.model_dump(mode='json')
    return True


@ui.page('/login')
def login() -> None:
    apply_theme()
    ui.dark_mode(True)
    if get_current_user() is not None:
        ui.navigate.to('/')
        return
    with (
        ui.column().classes('absolute-center items-center w-96 max-w-full gap-4'),
        ui.card().classes('w-full'),
        ui.column().classes('gap-4 q-pa-md'),
    ):
        ui.icon('🆘').classes('text-h4')
        ui.label('SOS Reclamos').classes('text-h5')
        username = ui.input('Usuario').props('outlined')
        password = ui.input(
            'Contraseña', password=True, password_toggle_button=True
        ).props('outlined')

        def submit() -> None:
            if _try_login(username.value or '', password.value or ''):
                ui.navigate.to('/')

        ui.button('Ingresar', on_click=submit).props(
            'unelevated color=primary full-width'
        )
