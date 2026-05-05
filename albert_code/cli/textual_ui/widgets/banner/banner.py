from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from albert_code.cli.textual_ui.widgets.banner.albert_logo import AlbertLogo
from albert_code.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic
from albert_code.core.config import VibeConfig
from albert_code.core.skills.manager import SkillManager


@dataclass
class BannerState:
    models_count: int = 0
    mcp_servers_count: int = 0
    skills_count: int = 0


class Banner(Static):
    state = reactive(BannerState(), init=False)

    def __init__(
        self, config: VibeConfig, skill_manager: SkillManager, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.can_focus = False
        self._initial_state = BannerState(
            models_count=len(config.models),
            mcp_servers_count=len(config.mcp_servers),
            skills_count=len(skill_manager.available_skills),
        )
        self._animated = not config.disable_welcome_banner_animation

    def compose(self) -> ComposeResult:
        with Horizontal(id="banner-container"):
            yield AlbertLogo()

            with Vertical(id="banner-info"):
                with Horizontal(classes="banner-line"):
                    yield NoMarkupStatic(
                        "", id="banner-models-count", classes="banner-meta"
                    )
                with Horizontal(classes="banner-line"):
                    yield NoMarkupStatic(
                        "", id="banner-extras-count", classes="banner-meta"
                    )
                with Horizontal(classes="banner-line"):
                    yield NoMarkupStatic("Type ", classes="banner-meta")
                    yield NoMarkupStatic("/help", classes="banner-cmd")
                    yield NoMarkupStatic(" for more information", classes="banner-meta")

    def on_mount(self) -> None:
        self.state = self._initial_state

    def watch_state(self) -> None:
        self.query_one("#banner-models-count", NoMarkupStatic).update(
            self._format_models_count()
        )
        self.query_one("#banner-extras-count", NoMarkupStatic).update(
            self._format_extras_count()
        )

    def freeze_animation(self) -> None:
        # Logo is static; nothing to freeze. Kept for API compatibility.
        return

    def set_state(self, config: VibeConfig, skill_manager: SkillManager) -> None:
        self.state = BannerState(
            models_count=len(config.models),
            mcp_servers_count=len(config.mcp_servers),
            skills_count=len(skill_manager.available_skills),
        )

    def _format_models_count(self) -> str:
        n = self.state.models_count
        return f"{n} model{'s' if n != 1 else ''}"

    def _format_extras_count(self) -> str:
        m = self.state.mcp_servers_count
        s = self.state.skills_count
        return (
            f"{m} MCP server{'s' if m != 1 else ''} · {s} skill{'s' if s != 1 else ''}"
        )
