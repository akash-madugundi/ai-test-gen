from pathlib import Path

import typer
from dotenv import load_dotenv

from orchestration.pipeline_controller import PipelineController
from utils.logger import get_logger

app = typer.Typer(help="AI Java test generation using Qwen")
logger = get_logger(__name__)

# Load .env from project root so QWEN_API_KEY and GITHUB_TOKEN are available.
load_dotenv(Path(__file__).resolve().parent / ".env")


@app.command()
def run(
    github_url: str | None = typer.Option(None, help="GitHub repository URL"),
    local_path: str | None = typer.Option(None, help="Local repository path"),
    create_pr: bool = typer.Option(False, help="Create GitHub PR (GitHub mode)"),
    repo_full_name: str | None = typer.Option(None, help="owner/repo for PR creation"),
    base_branch: str = typer.Option("main", help="Base branch for PR"),
    push_branch: bool = typer.Option(False, help="Push branch to origin before PR"),
) -> None:
    if bool(github_url) == bool(local_path):
        raise typer.BadParameter("Provide exactly one of --github-url or --local-path")

    controller = PipelineController(root_dir=Path(__file__).resolve().parent)
    result = controller.run(
        github_url=github_url,
        local_path=local_path,
        create_pr=create_pr,
        repo_full_name=repo_full_name,
        base_branch=base_branch,
        push_branch=push_branch,
    )

    logger.info("Generation complete")
    logger.info("Repo Dir: %s", result["repo_dir"])
    logger.info("Build System: %s", result.get("build_system", "unknown"))
    logger.info("Generated Files: %s", len(result["generated_test_files"]))
    logger.info("Line Coverage: %.2f%%", result["line_coverage"])
    logger.info("Branch Coverage: %.2f%%", result["branch_coverage"])
    logger.info("Elapsed Time: %.2fs", result.get("elapsed_seconds", 0.0))
    if result.get("branch_name"):
        logger.info("Branch: %s", result["branch_name"])
    if result.get("pr_url"):
        logger.info("PR: %s", result["pr_url"])


if __name__ == "__main__":
    app()
