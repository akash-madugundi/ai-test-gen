import os

from github import Github


def create_pull_request(repo_full_name: str, title: str, body: str, head_branch: str, base_branch: str = "main") -> str:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("GITHUB_TOKEN is not set")

    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
    return pr.html_url
