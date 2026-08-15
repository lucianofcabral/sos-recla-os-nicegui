"""Formatting helpers for the UI layer (Argentine conventions)."""

from datetime import date


def format_money(value: float | None) -> str:
    """Format a money value with '.' thousands, ',' decimals, two decimals."""
    if value is None:
        return ''
    formatted = f'{value:,.2f}'
    return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')


def format_date(value: date | None) -> str:
    """Format a date as YYYY-MM-DD (empty string when None)."""
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d')
