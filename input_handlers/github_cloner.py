import shutil
from pathlib import Path

from git import Repo

from utils.file_utils import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)


def clone_github_repo(repo_url: str, workspace_dir: Path) -> Path:
    ensure_dir(workspace_dir)
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_dir = workspace_dir / repo_name

    if target_dir.exists():
        logger.info("Removing existing directory before clone: %s", target_dir)
        shutil.rmtree(target_dir)

    logger.info("Cloning repository from %s", repo_url)
    Repo.clone_from(repo_url, target_dir)
    return target_dir
