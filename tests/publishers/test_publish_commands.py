"""Tests for publish_project and publish_aap functions."""

from unittest.mock import patch

import pytest

from src.publishers.publish import publish_aap, publish_project
from src.publishers.tools import AAPSyncResult


class TestPublishProject:
    """Tests for the publish_project function."""

    def test_single_role_creates_structure(self, sample_role_dir, tmp_path):
        base = tmp_path / "output"
        base.mkdir()

        result = publish_project(
            module_names=["my_role"],
            source_paths=[sample_role_dir],
            base_path=str(base),
        )

        assert "my_role" in result
        from pathlib import Path

        project = Path(result)
        assert (project / "ansible.cfg").exists()
        assert (project / "collections" / "requirements.yml").exists()
        assert (project / "inventory" / "hosts.yml").exists()
        assert (project / "roles" / "my_role" / "tasks" / "main.yml").exists()
        assert (project / "playbooks" / "run_my_role.yml").exists()

    def test_multiple_roles_creates_structure(
        self, sample_role_dir, sample_role_dir2, tmp_path
    ):
        base = tmp_path / "output"
        base.mkdir()

        result = publish_project(
            module_names=["role_a", "role_b"],
            source_paths=[sample_role_dir, sample_role_dir2],
            base_path=str(base),
        )

        from pathlib import Path

        project = Path(result)
        assert (project / "roles" / "role_a").exists()
        assert (project / "roles" / "role_b").exists()
        assert (project / "playbooks" / "run_role_a.yml").exists()
        assert (project / "playbooks" / "run_role_b.yml").exists()

    def test_mismatched_names_and_paths_raises(self, sample_role_dir):
        with pytest.raises(ValueError, match="must match"):
            publish_project(
                module_names=["a", "b"],
                source_paths=[sample_role_dir],
            )

    def test_missing_source_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            publish_project(
                module_names=["my_role"],
                source_paths=[str(tmp_path / "nonexistent")],
                base_path=str(tmp_path),
            )

    def test_with_collections_file(self, sample_role_dir, tmp_path):
        base = tmp_path / "output"
        base.mkdir()

        collections_file = tmp_path / "collections.yml"
        collections_file.write_text(
            '- name: community.general\n  version: ">=5.0.0"\n'
        )

        result = publish_project(
            module_names=["my_role"],
            source_paths=[sample_role_dir],
            base_path=str(base),
            collections_file=str(collections_file),
        )

        from pathlib import Path

        project = Path(result)
        assert (project / "collections" / "requirements.yml").exists()


class TestPublishAAP:
    """Tests for the publish_aap function."""

    def test_aap_not_configured_raises(self):
        with pytest.raises(RuntimeError, match="not configured"):
            publish_aap(
                repo_url="https://github.com/org/repo.git",
                branch="main",
            )

    @patch("src.publishers.publish.sync_to_aap")
    def test_aap_error_raises(self, mock_sync):
        mock_sync.return_value = AAPSyncResult.from_error("Connection refused")

        with pytest.raises(RuntimeError, match="Connection refused"):
            publish_aap(
                repo_url="https://github.com/org/repo.git",
                branch="main",
            )

    @patch("src.publishers.publish.sync_to_aap")
    def test_aap_success(self, mock_sync):
        mock_sync.return_value = AAPSyncResult(
            enabled=True,
            project_name="test-project",
            project_id=42,
            project_update_id=100,
            project_update_status="pending",
        )

        result = publish_aap(
            repo_url="https://github.com/org/repo.git",
            branch="main",
        )

        assert result.project_name == "test-project"
        assert result.project_id == 42
        mock_sync.assert_called_once_with(
            repository_url="https://github.com/org/repo.git",
            branch="main",
        )
