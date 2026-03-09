from enum import Enum


class WorkflowType(str, Enum):
    GITHUB = "github"
    LOCAL = "local"


def choose_workflow(github_url: str | None, local_path: str | None) -> WorkflowType:
    if github_url:
        return WorkflowType.GITHUB
    if local_path:
        return WorkflowType.LOCAL
    raise ValueError("Either github_url or local_path must be provided")
