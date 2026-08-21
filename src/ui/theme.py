"""Professional colorful theme for SOS Reclamos.

Centralizes the Quasar brand palette (via ``ui.colors``) and custom CSS so the
whole UI gets a coherent, colorful-but-professional look in both light and dark
modes. Apply once at startup with :func:`apply_theme`.
"""

from __future__ import annotations

from nicegui import ui

# Brand palette (Tailwind-inspired: vibrant yet professional).
PRIMARY = '#4F46E5'  # Indigo 600
SECONDARY = '#0D9488'  # Teal 600
ACCENT = '#8B5CF6'  # Violet 500
DARK = '#0F172A'  # Slate 900 (dark mode background)
DARK_PAGE = '#1E293B'  # Slate 800 (dark surfaces)
POSITIVE = '#16A34A'  # Green 600
NEGATIVE = '#DC2626'  # Red 600
INFO = '#2563EB'  # Blue 600
WARNING = '#D97706'  # Amber 600

_CSS = """
/* ===== SOS Reclamos — Professional colorful theme ===== */

:root {
  --sos-primary: #4F46E5;
  --sos-secondary: #0D9488;
  --sos-accent: #8B5CF6;
}

/* Header: brand gradient that reads well in light and dark modes */
.q-header {
  background: linear-gradient(120deg, #4F46E5 0%, #7C3AED 45%, #0D9488 100%) !important;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.28) !important;
  backdrop-filter: blur(6px);
}

/* Header buttons: always white text with a subtle hover tint */
.q-header .q-btn,
.q-header .q-btn .q-icon {
  color: #ffffff !important;
}
.q-header .q-btn:hover {
  background: rgba(255, 255, 255, 0.16) !important;
}

/* Cards: rounded with a soft shadow and a gentle lift on hover */
.q-card {
  border-radius: 14px;
  box-shadow: 0 6px 22px rgba(15, 23, 42, 0.08);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.q-card:hover {
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
}

/* Tables: comfortable rows, zebra striping and clear hover states */

.q-table__middle td {
  padding-top: 11px;
  padding-bottom: 11px;
}
body:not(.q-dark) .q-table tbody tr:nth-child(even) {
  background: rgba(79, 70, 229, 0.04);
}
body:not(.q-dark) .q-table tbody tr:hover {
  background: rgba(13, 148, 136, 0.10) !important;
}
.q-dark .q-table tbody tr:nth-child(even) {
  background: rgba(255, 255, 255, 0.03);
}
.q-dark .q-table tbody tr:hover {
  background: rgba(139, 92, 246, 0.16) !important;
}

/* Inputs and dialogs: a touch rounder for a friendlier feel */
.q-field__control {
  border-radius: 10px;
}
.q-dialog .q-card {
  border-radius: 16px;
}

/* Buttons: subtle press feedback */
.q-btn {
  transition: transform 0.12s ease, box-shadow 0.2s ease;
}
.q-btn:active {
  transform: translateY(1px);
}

/* Active tab emphasis in the header */
.q-header .q-tabs .q-tab--active {
  font-weight: 600;
}
"""

def apply_theme() -> None:
    """Apply the color palette and custom CSS to the current page context.

    Call this inside a page-building function (e.g. the shared shell) rather
    than at startup, so it coexists with NiceGUI's ``ui.page`` script mode.
    """
    ui.colors(
        primary=PRIMARY,
        secondary=SECONDARY,
        accent=ACCENT,
        dark=DARK,
        dark_page=DARK_PAGE,
        positive=POSITIVE,
        negative=NEGATIVE,
        info=INFO,
        warning=WARNING,
    )
    ui.add_css(_CSS)
