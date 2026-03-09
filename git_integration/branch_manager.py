from datetime import datetime
from pathlib import Path

from git import Repo


def create_ai_branch(repo_dir: Path) -> str:
    repo = Repo(repo_dir)
    branch_name = f"ai-test-generation/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    repo.git.checkout("-b", branch_name)
    return branch_name
