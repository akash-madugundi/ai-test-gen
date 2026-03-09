from pathlib import Path

from utils.command_executor import CommandResult, run_command


class MavenRunner:
    def __init__(self, test_cmd: str, jacoco_cmd: str) -> None:
        self.test_cmd = test_cmd
        self.jacoco_cmd = jacoco_cmd

    def run_tests(self, repo_dir: Path) -> CommandResult:
        return run_command(self.test_cmd, cwd=repo_dir)

    def run_jacoco_report(self, repo_dir: Path) -> CommandResult:
        return run_command(self.jacoco_cmd, cwd=repo_dir)
