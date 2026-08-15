"""Tests for the formatting helpers (Argentine conventions)."""

from __future__ import annotations

from datetime import date

from src.application.format import format_date, format_money


def test_format_money_argentine_style() -> None:
    assert format_money(1234.5) == '1.234,50'
    assert format_money(15000) == '15.000,00'
    assert format_money(0) == '0,00'
    assert format_money(0.0) == '0,00'
    assert format_money(None) == ''


def test_format_date_iso_yyyy_mm_dd() -> None:
    assert format_date(date(2026, 8, 12)) == '2026-08-12'
    assert format_date(None) == ''
