from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from albert_code.core.paths.config_paths import (
    discover_local_agents_dirs,
    discover_local_skills_dirs,
    discover_local_tools_dirs,
)


class TestDiscoverLocalSkillsDirs:
    def test_returns_empty_list_when_dir_not_trusted(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "skills").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = False
            assert discover_local_skills_dirs(tmp_path) == []

    def test_returns_empty_list_when_trusted_but_no_skills_dirs(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            assert discover_local_skills_dirs(tmp_path) == []

    def test_returns_vibe_skills_only_when_only_it_exists(self, tmp_path: Path) -> None:
        vibe_skills = tmp_path / ".albert-code" / "skills"
        vibe_skills.mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_skills_dirs(tmp_path)
        assert result == [vibe_skills]

    def test_returns_agents_skills_only_when_only_it_exists(
        self, tmp_path: Path
    ) -> None:
        agents_skills = tmp_path / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_skills_dirs(tmp_path)
        assert result == [agents_skills]

    def test_returns_both_in_order_when_both_exist(self, tmp_path: Path) -> None:
        vibe_skills = tmp_path / ".albert-code" / "skills"
        agents_skills = tmp_path / ".agents" / "skills"
        vibe_skills.mkdir(parents=True)
        agents_skills.mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_skills_dirs(tmp_path)
        assert result == [vibe_skills, agents_skills]

    def test_ignores_vibe_skills_when_file_not_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code").mkdir()
        (tmp_path / ".albert-code" / "skills").write_text("", encoding="utf-8")
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_skills_dirs(tmp_path)
        assert result == []

    def test_finds_skills_dirs_recursively_in_trusted_folder(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".albert-code" / "skills").mkdir(parents=True)
        (tmp_path / "sub" / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / "sub" / "deep" / ".albert-code" / "skills").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_skills_dirs(tmp_path)
        assert result == [
            tmp_path / ".albert-code" / "skills",
            tmp_path / "sub" / ".agents" / "skills",
            tmp_path / "sub" / "deep" / ".albert-code" / "skills",
        ]

    def test_does_not_descend_into_ignored_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "skills").mkdir(parents=True)
        (tmp_path / "node_modules" / ".albert-code" / "skills").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_skills_dirs(tmp_path)
        assert result == [tmp_path / ".albert-code" / "skills"]


class TestDiscoverLocalToolsDirs:
    def test_returns_empty_list_when_dir_not_trusted(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "tools").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = False
            assert discover_local_tools_dirs(tmp_path) == []

    def test_returns_empty_list_when_trusted_but_no_tools_dir(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            assert discover_local_tools_dirs(tmp_path) == []

    def test_returns_tools_dir_when_exists(self, tmp_path: Path) -> None:
        vibe_tools = tmp_path / ".albert-code" / "tools"
        vibe_tools.mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_tools_dirs(tmp_path)
        assert result == [vibe_tools]

    def test_ignores_tools_when_file_not_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code").mkdir()
        (tmp_path / ".albert-code" / "tools").write_text("", encoding="utf-8")
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_tools_dirs(tmp_path)
        assert result == []

    def test_finds_tools_dirs_recursively(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "tools").mkdir(parents=True)
        (tmp_path / "sub" / ".albert-code" / "tools").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_tools_dirs(tmp_path)
        assert result == [
            tmp_path / ".albert-code" / "tools",
            tmp_path / "sub" / ".albert-code" / "tools",
        ]

    def test_does_not_descend_into_ignored_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "tools").mkdir(parents=True)
        (tmp_path / ".git" / ".albert-code" / "tools").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_tools_dirs(tmp_path)
        assert result == [tmp_path / ".albert-code" / "tools"]


class TestDiscoverLocalAgentsDirs:
    def test_returns_empty_list_when_dir_not_trusted(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "agents").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = False
            assert discover_local_agents_dirs(tmp_path) == []

    def test_returns_empty_list_when_trusted_but_no_agents_dir(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            assert discover_local_agents_dirs(tmp_path) == []

    def test_returns_agents_dir_when_exists(self, tmp_path: Path) -> None:
        vibe_agents = tmp_path / ".albert-code" / "agents"
        vibe_agents.mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_agents_dirs(tmp_path)
        assert result == [vibe_agents]

    def test_ignores_agents_when_file_not_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code").mkdir()
        (tmp_path / ".albert-code" / "agents").write_text("", encoding="utf-8")
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_agents_dirs(tmp_path)
        assert result == []

    def test_finds_agents_dirs_recursively(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "agents").mkdir(parents=True)
        (tmp_path / "sub" / "deep" / ".albert-code" / "agents").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_agents_dirs(tmp_path)
        assert result == [
            tmp_path / ".albert-code" / "agents",
            tmp_path / "sub" / "deep" / ".albert-code" / "agents",
        ]

    def test_does_not_descend_into_ignored_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".albert-code" / "agents").mkdir(parents=True)
        (tmp_path / "__pycache__" / ".albert-code" / "agents").mkdir(parents=True)
        with patch(
            "albert_code.core.paths.config_paths.trusted_folders_manager"
        ) as mock_tfm:
            mock_tfm.is_trusted.return_value = True
            result = discover_local_agents_dirs(tmp_path)
        assert result == [tmp_path / ".albert-code" / "agents"]
