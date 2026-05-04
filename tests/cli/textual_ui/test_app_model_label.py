"""Unit tests for `VibeApp._format_model_label`.

Covers the bottom-bar display of the active model, especially the
auto-fallback transition where the agent loop temporarily routes to the
secondary model and the footer should surface that with a `↳` prefix
instead of `⚙`.

The function only reads `self.config` and `self.agent_loop`; we bypass
Textual mounting by calling the unbound method with a `SimpleNamespace`
stub.
"""

from __future__ import annotations

from types import SimpleNamespace

from albert_code.cli.textual_ui.app import VibeApp
from albert_code.core.config import ModelConfig


def _make_model(alias: str, name: str, fallback: str | None = None) -> ModelConfig:
    return ModelConfig(
        name=name, provider="albert", alias=alias, fallback_model=fallback
    )


def _make_stub(
    *, active_alias: str, models: list[ModelConfig], last_resolved: str | None
) -> SimpleNamespace:
    config = SimpleNamespace(
        active_model=active_alias,
        models=models,
        get_active_model=lambda: next(m for m in models if m.alias == active_alias),
    )
    agent_loop = SimpleNamespace(_last_resolved_model_alias=last_resolved)
    return SimpleNamespace(config=config, agent_loop=agent_loop)


class TestFormatModelLabelPrimary:
    def test_shows_alias_and_short_name_with_gear_prefix(self) -> None:
        primary = _make_model("albert-code", "Qwen/Qwen3-Coder-30B-A3B-Instruct")
        stub = _make_stub(
            active_alias="albert-code", models=[primary], last_resolved="albert-code"
        )
        label = VibeApp._format_model_label(stub)
        assert label == "⚙ albert-code (Qwen3-Coder-30B-A3B-Instruct)"

    def test_no_resolved_alias_yet_falls_back_to_primary(self) -> None:
        primary = _make_model("albert-code", "Qwen/Qwen3-Coder-30B-A3B-Instruct")
        stub = _make_stub(
            active_alias="albert-code", models=[primary], last_resolved=None
        )
        label = VibeApp._format_model_label(stub)
        assert label.startswith("⚙ ")
        assert "albert-code" in label

    def test_alias_equals_short_name_collapses_to_one(self) -> None:
        primary = _make_model("solo", "solo")
        stub = _make_stub(active_alias="solo", models=[primary], last_resolved="solo")
        label = VibeApp._format_model_label(stub)
        assert label == "⚙ solo"


class TestFormatModelLabelFallback:
    def test_fallback_active_uses_arrow_prefix_and_shows_secondary(self) -> None:
        primary = _make_model(
            "albert-code", "Qwen/Qwen3-Coder-30B-A3B-Instruct", fallback="albert-large"
        )
        secondary = _make_model("albert-large", "openai/gpt-oss-120b")
        stub = _make_stub(
            active_alias="albert-code",
            models=[primary, secondary],
            last_resolved="albert-large",
        )
        label = VibeApp._format_model_label(stub)
        assert label == "↳ albert-large (gpt-oss-120b)"
        assert "Qwen" not in label

    def test_fallback_back_to_primary_shows_gear_again(self) -> None:
        """Once the auto-fallback expires, agent loop resets the alias."""
        primary = _make_model(
            "albert-code", "Qwen/Qwen3-Coder-30B-A3B-Instruct", fallback="albert-large"
        )
        secondary = _make_model("albert-large", "openai/gpt-oss-120b")
        stub = _make_stub(
            active_alias="albert-code",
            models=[primary, secondary],
            last_resolved="albert-code",
        )
        label = VibeApp._format_model_label(stub)
        assert label.startswith("⚙ ")
        assert "albert-code" in label

    def test_unknown_resolved_alias_does_not_break_label(self) -> None:
        """Defensive: agent loop reports an alias that is not in config.models."""
        primary = _make_model("albert-code", "Qwen/Qwen3-Coder-30B-A3B-Instruct")
        stub = _make_stub(
            active_alias="albert-code", models=[primary], last_resolved="something-else"
        )
        label = VibeApp._format_model_label(stub)
        # No matching candidate -> stays on primary, gear prefix.
        assert label.startswith("⚙ ")
        assert "albert-code" in label


class TestFormatModelLabelMissingConfig:
    def test_invalid_active_model_returns_raw_value(self) -> None:
        """If get_active_model raises, the label falls back to the raw string."""

        def _raise() -> ModelConfig:
            raise ValueError("not found")

        config = SimpleNamespace(
            active_model="ghost-model", models=[], get_active_model=_raise
        )
        agent_loop = SimpleNamespace(_last_resolved_model_alias=None)
        stub = SimpleNamespace(config=config, agent_loop=agent_loop)

        label = VibeApp._format_model_label(stub)
        assert label == "⚙ ghost-model"
