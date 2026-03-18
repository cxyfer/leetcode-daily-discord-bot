import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
README_PATH = REPO_ROOT / "README.md"
CLAUDE_PATH = REPO_ROOT / "CLAUDE.md"
TESTS_ROOT = REPO_ROOT / "tests"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_pyproject() -> dict:
    with PYPROJECT_PATH.open("rb") as file:
        return tomllib.load(file)


def test_pytest_config_uses_src_pythonpath_and_packaged_coverage():
    config = _load_pyproject()["tool"]["pytest"]["ini_options"]
    addopts = config["addopts"]
    if isinstance(addopts, list):
        addopts = " ".join(addopts)

    assert config.get("pythonpath") == ["src"]
    assert "--import-mode=importlib" in addopts
    assert "--cov=src/bot" in addopts
    assert "--cov=." not in addopts


def test_existing_tests_do_not_mutate_sys_path_for_src_imports():
    hacked_files = []
    for test_file in sorted(TESTS_ROOT.glob("test_*.py")):
        if test_file.name == Path(__file__).name:
            continue
        contents = _read_text(test_file)
        if "sys.path.insert(" in contents or "sys.path.append(" in contents:
            hacked_files.append(test_file.name)

    assert hacked_files == []


def test_claude_md_contract_is_optional_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sys.modules[__name__], "CLAUDE_PATH", tmp_path / "missing-CLAUDE.md")

    test_claude_md_matches_packaged_runtime_contract()


def test_claude_md_matches_packaged_runtime_contract():
    if not CLAUDE_PATH.is_file():
        return

    claude_md = _read_text(CLAUDE_PATH)

    assert "src/bot/" in claude_md
    assert "src/bot/cogs/" in claude_md
    assert "src/bot/utils/" in claude_md
    assert "uv run bot.py" in claude_md
    assert "bot.api_client" in claude_md
    assert "bot.cogs.similar_cog" in claude_md
    assert "embedding_cli.py" not in claude_md
    assert "embeddings/" not in claude_md
    assert "migrate_embeddings.sql" not in claude_md
