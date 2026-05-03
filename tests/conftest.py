from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest
import tomli_w

from albert_code.cli.textual_ui.app import CORE_VERSION, VibeApp
from albert_code.core.agent_loop import AgentLoop
from albert_code.core.agents.models import BuiltinAgentName
from albert_code.core.config import SessionLoggingConfig, VibeConfig
from albert_code.core.llm.types import BackendLike
from albert_code.core.paths import global_paths
from albert_code.core.paths.config_paths import unlock_config_paths
from tests.stubs.fake_backend import FakeBackend
from tests.update_notifier.adapters.fake_update_cache_repository import (
    FakeUpdateCacheRepository,
)
from tests.update_notifier.adapters.fake_update_gateway import FakeUpdateGateway


def get_base_config() -> dict[str, Any]:
    return {
        "active_model": "devstral-latest",
        "providers": [
            {
                "name": "mistral",
                "api_base": "https://api.mistral.ai/v1",
                "api_key_env_var": "MISTRAL_API_KEY",
                "backend": "mistral",
            }
        ],
        "models": [
            {
                "name": "albert-code-cli-latest",
                "provider": "mistral",
                "alias": "devstral-latest",
            }
        ],
        "enable_auto_update": False,
    }


@pytest.fixture(autouse=True)
def _reset_throttlers() -> None:
    from albert_code.core.llm.throttling import reset_throttlers_for_tests

    reset_throttlers_for_tests()


@pytest.fixture(autouse=True)
def tmp_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    tmp_working_directory = tmp_path_factory.mktemp("test_cwd")
    monkeypatch.chdir(tmp_working_directory)
    return tmp_working_directory


@pytest.fixture(autouse=True)
def config_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    tmp_path = tmp_path_factory.mktemp("albert_code")
    config_dir = tmp_path / ".albert-code"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(tomli_w.dumps(get_base_config()), encoding="utf-8")

    monkeypatch.setattr(global_paths, "_DEFAULT_ALBERT_CODE_HOME", config_dir)
    return config_dir


@pytest.fixture(autouse=True)
def _unlock_config_paths():
    unlock_config_paths()


@pytest.fixture(autouse=True)
def _mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "mock")


@pytest.fixture(autouse=True)
def _mock_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock platform to be Linux with /bin/sh shell for consistent test behavior.

    This ensures that platform-specific system prompt generation is consistent
    across all tests regardless of the actual platform running the tests.
    """
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("SHELL", "/bin/sh")


@pytest.fixture(autouse=True)
def _mock_update_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "albert_code.cli.update_notifier.update.UPDATE_COMMANDS", ["true"]
    )


@pytest.fixture(autouse=True)
def telemetry_events(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    def record_telemetry(
        self: Any, event_name: str, properties: dict[str, Any]
    ) -> None:
        events.append({"event_name": event_name, "properties": properties})

    monkeypatch.setattr(
        "albert_code.core.telemetry.send.TelemetryClient.send_telemetry_event",
        record_telemetry,
    )
    return events


@pytest.fixture
def vibe_app() -> VibeApp:
    return build_test_vibe_app()


@pytest.fixture
def agent_loop() -> AgentLoop:
    return build_test_agent_loop()


@pytest.fixture
def vibe_config() -> VibeConfig:
    return build_test_vibe_config()


def build_test_vibe_config(**kwargs) -> VibeConfig:
    session_logging = kwargs.pop("session_logging", None)
    resolved_session_logging = (
        SessionLoggingConfig(enabled=False)
        if session_logging is None
        else session_logging
    )
    enable_update_checks = kwargs.pop("enable_update_checks", None)
    resolved_enable_update_checks = (
        False if enable_update_checks is None else enable_update_checks
    )
    return VibeConfig(
        session_logging=resolved_session_logging,
        enable_update_checks=resolved_enable_update_checks,
        **kwargs,
    )


def build_test_agent_loop(
    *,
    config: VibeConfig | None = None,
    agent_name: str = BuiltinAgentName.DEFAULT,
    backend: BackendLike | None = None,
    enable_streaming: bool = False,
    **kwargs,
) -> AgentLoop:

    resolved_config = config or build_test_vibe_config()

    return AgentLoop(
        config=resolved_config,
        agent_name=agent_name,
        backend=backend or FakeBackend(),
        enable_streaming=enable_streaming,
        **kwargs,
    )


def build_test_vibe_app(
    *, config: VibeConfig | None = None, agent_loop: AgentLoop | None = None, **kwargs
) -> VibeApp:
    app_config = config or build_test_vibe_config()

    resolved_agent_loop = agent_loop or build_test_agent_loop(config=app_config)

    update_notifier = kwargs.pop("update_notifier", None)
    resolved_update_notifier = (
        FakeUpdateGateway() if update_notifier is None else update_notifier
    )
    update_cache_repository = kwargs.pop("update_cache_repository", None)
    resolved_update_cache_repository = (
        FakeUpdateCacheRepository()
        if update_cache_repository is None
        else update_cache_repository
    )
    kwargs.pop("plan_offer_gateway", None)
    current_version = kwargs.pop("current_version", None)
    resolved_current_version = (
        CORE_VERSION if current_version is None else current_version
    )

    return VibeApp(
        agent_loop=resolved_agent_loop,
        current_version=resolved_current_version,
        update_notifier=resolved_update_notifier,
        update_cache_repository=resolved_update_cache_repository,
        initial_prompt=kwargs.pop("initial_prompt", None),
        **kwargs,
    )
