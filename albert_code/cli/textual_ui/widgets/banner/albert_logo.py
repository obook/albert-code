from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

from albert_code import __version__

# Tricolor inspired by the French flag, but lifted toward more luminous
# values so the logo stays readable on dark terminals. The textbook
# `#002395` flag blue is too dim against a black background.
_BLUE = "#318CE7"  # "Bleu de France" (lighter than the official #002395)
_WHITE = "#FFFFFF"
_RED = "#ED2939"


def _line(text: str, color: str) -> str:
    return f"[{color}]{text}[/]"


_LOGO = "\n".join([
    _line(r"    _    _ _               _   ", _BLUE),
    _line(r"   / \  | | |__   ___ _ __| |_ ", _BLUE),
    _line(r"  / _ \ | | '_ \ / _ \ '__| __|", _WHITE),
    _line(r" / ___ \| | |_) |  __/ |  | |_ ", _WHITE),
    _line(r"/_/   \_\_|_.__/ \___|_|   \__|", _RED),
    _line(rf"                  code v{__version__}", _RED),
])


class AlbertLogo(Static):
    """Albert Code ASCII logo in French tricolor (blue / white / red)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, classes="albert-logo")

    def compose(self) -> ComposeResult:
        yield Static(_LOGO, classes="albert-logo-text", markup=True)
