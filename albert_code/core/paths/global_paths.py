from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path

from albert_code import ALBERT_CODE_ROOT


class GlobalPath:
    def __init__(self, resolver: Callable[[], Path]) -> None:
        self._resolver = resolver

    @property
    def path(self) -> Path:
        return self._resolver()


_DEFAULT_ALBERT_CODE_HOME = Path.home() / ".albert-code"


def _get_vibe_home() -> Path:
    if vibe_home := os.getenv("ALBERT_CODE_HOME"):
        return Path(vibe_home).expanduser().resolve()
    return _DEFAULT_ALBERT_CODE_HOME


ALBERT_CODE_HOME = GlobalPath(_get_vibe_home)
GLOBAL_CONFIG_FILE = GlobalPath(lambda: ALBERT_CODE_HOME.path / "config.toml")
GLOBAL_ENV_FILE = GlobalPath(lambda: ALBERT_CODE_HOME.path / ".env")
GLOBAL_TOOLS_DIR = GlobalPath(lambda: ALBERT_CODE_HOME.path / "tools")
GLOBAL_SKILLS_DIR = GlobalPath(lambda: ALBERT_CODE_HOME.path / "skills")
GLOBAL_AGENTS_DIR = GlobalPath(lambda: ALBERT_CODE_HOME.path / "agents")
GLOBAL_PROMPTS_DIR = GlobalPath(lambda: ALBERT_CODE_HOME.path / "prompts")
SESSION_LOG_DIR = GlobalPath(lambda: ALBERT_CODE_HOME.path / "logs" / "session")
TRUSTED_FOLDERS_FILE = GlobalPath(
    lambda: ALBERT_CODE_HOME.path / "trusted_folders.toml"
)
LOG_DIR = GlobalPath(lambda: ALBERT_CODE_HOME.path / "logs")
LOG_FILE = GlobalPath(lambda: ALBERT_CODE_HOME.path / "logs" / "albert-code.log")

DEFAULT_TOOL_DIR = GlobalPath(lambda: ALBERT_CODE_ROOT / "core" / "tools" / "builtins")
