from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

_BLUE = "#002395"
_WHITE = "#FFFFFF"
_RED = "#ED2939"

_B = f"[{_BLUE}]\u2588[/]"
_W = f"[{_WHITE}]\u2588[/]"
_R = f"[{_RED}]\u2588[/]"

_FLAG = "\n".join([
    f"{_B}{_B}{_W}{_W}{_R}{_R}",
    f"{_B}{_B}{_W}{_W}{_R}{_R}",
    f"{_B}{_B}{_W}{_W}{_R}{_R}",
])


class PetitChat(Static):
    """Small French flag banner widget."""

    def __init__(self, animate: bool = True, **kwargs: Any) -> None:
        super().__init__(**kwargs, classes="banner-chat")
        self._do_animate = animate

    def compose(self) -> ComposeResult:
        yield Static(_FLAG, classes="petit-chat", markup=True)

    def freeze_animation(self) -> None:
        pass
