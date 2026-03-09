import shutil
from pathlib import Path

from utils.file_utils import ensure_dir


def load_local_repo(local_path: Path, workspace_dir: Path) -> Path:
    if not local_path.exists():
        raise FileNotFoundError(f"Local repository path not found: {local_path}")

    if not ((local_path / "pom.xml").exists() or (local_path / "build.gradle").exists()):
        raise ValueError("Provided path is not a Maven/Gradle project")

    ensure_dir(workspace_dir)
    target_dir = workspace_dir / local_path.name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(local_path, target_dir)
    return target_dir
