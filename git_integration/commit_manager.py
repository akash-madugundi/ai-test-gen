from pathlib import Path

from git import Repo


def commit_generated_tests(repo_dir: Path, message: str = "test: add AI generated unit tests") -> None:
    repo = Repo(repo_dir)
    repo.git.add(A=True)
    if repo.is_dirty(untracked_files=True):
        repo.index.commit(message)
