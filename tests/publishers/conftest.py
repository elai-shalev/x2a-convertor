import pytest


@pytest.fixture
def sample_role_dir(tmp_path) -> str:
    """Create a sample role directory structure."""
    role_dir = tmp_path / "sample_role"
    (role_dir / "tasks").mkdir(parents=True)
    (role_dir / "meta").mkdir()
    (role_dir / "tasks" / "main.yml").write_text(
        "- name: Test task\n  debug:\n    msg: Hello"
    )
    (role_dir / "meta" / "main.yml").write_text("---\ndependencies: []")
    return str(role_dir)


@pytest.fixture
def sample_role_dir2(tmp_path) -> str:
    """Create a second sample role directory structure."""
    role_dir = tmp_path / "sample_role2"
    (role_dir / "tasks").mkdir(parents=True)
    (role_dir / "meta").mkdir()
    (role_dir / "tasks" / "main.yml").write_text(
        "- name: Test task 2\n  debug:\n    msg: World"
    )
    (role_dir / "meta" / "main.yml").write_text("---\ndependencies: []")
    return str(role_dir)


@pytest.fixture
def project_with_module(tmp_path) -> tuple:
    """Create a project directory with a single module role at the expected path.

    Returns (project_id_path, module_name) where project_id_path is the
    absolute path to the project directory.
    """
    module_name = "my_role"
    project_dir = tmp_path / "proj123"
    role_dir = project_dir / "modules" / module_name / "ansible" / "roles" / module_name
    (role_dir / "tasks").mkdir(parents=True)
    (role_dir / "meta").mkdir()
    (role_dir / "tasks" / "main.yml").write_text(
        "- name: Test task\n  debug:\n    msg: Hello"
    )
    (role_dir / "meta" / "main.yml").write_text("---\ndependencies: []")
    return str(project_dir), module_name


@pytest.fixture
def second_module_in_project(tmp_path) -> tuple:
    """Create a project directory with two module roles.

    Returns (project_id_path, first_module, second_module).
    """
    project_dir = tmp_path / "proj456"
    for mod_name in ("role_a", "role_b"):
        role_dir = project_dir / "modules" / mod_name / "ansible" / "roles" / mod_name
        (role_dir / "tasks").mkdir(parents=True)
        (role_dir / "meta").mkdir()
        (role_dir / "tasks" / "main.yml").write_text(
            f"- name: Test task {mod_name}\n  debug:\n    msg: Hello"
        )
        (role_dir / "meta" / "main.yml").write_text("---\ndependencies: []")
    return str(project_dir), "role_a", "role_b"
