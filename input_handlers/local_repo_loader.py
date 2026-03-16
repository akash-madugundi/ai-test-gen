import os
import shutil
import stat
from pathlib import Path

from utils.file_utils import ensure_dir


def load_local_repo(local_path: Path, workspace_dir: Path) -> Path:
    if not local_path.exists():
        raise FileNotFoundError(f"Local repository path not found: {local_path}")

    if not ((local_path / "pom.xml").exists() or (local_path / "build.gradle").exists()):
        raise ValueError("Provided path is not a Maven/Gradle project")

    ensure_dir(workspace_dir)
    target_dir = workspace_dir / local_path.name

    def _ignore(_: str, names: list[str]) -> set[str]:
        # Skip metadata and large folders that can cause copy and permission problems.
        skip = {
            ".idea",
            ".git",
            ".vscode",
            ".gradle",
            "build",
            "target",
            "node_modules",
            "__pycache__",
        }
        return skip.intersection(set(names))

    def _on_rm_error(func, path, _exc_info):
        # Windows: clear read-only bit and retry.
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if target_dir.exists():
        shutil.rmtree(target_dir, onerror=_on_rm_error)
    shutil.copytree(local_path, target_dir, ignore=_ignore)
    return target_dir
