import re
from pathlib import Path

from auto_reviewer import codex, github_client, prompts, workspace

_LOCAL_LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?://|#|mailto:)[^)\s]+\)")


def _sanitize(text: str, cwd: Path) -> str:
    """Remove worktree absolute paths and unwrap markdown links to local files."""
    cwd_str = str(cwd).rstrip("/")
    text = text.replace(cwd_str + "/", "")
    text = text.replace(cwd_str, "")
    return _LOCAL_LINK_RE.sub(r"\1", text)


def design_review(repo: str, issue_number: int) -> None:
    issue = github_client.get_issue(repo, issue_number)
    cwd = workspace.prepare_issue_workspace(repo, issue_number)
    prompt = prompts.DESIGN_REVIEW_PROMPT.format(
        title=issue.get("title", ""),
        body=issue.get("body") or "",
    )
    raw = codex.run_codex(prompt, cwd=cwd, sandbox_mode="workspace-write")
    cleaned = _sanitize(raw, cwd)
    github_client.post_comment(repo, issue_number, prompts.with_bot_prefix(cleaned))


def code_review(repo: str, pr_number: int) -> None:
    pr = github_client.get_issue(repo, pr_number)
    cwd = workspace.prepare_pr_workspace(repo, pr_number)
    diff = github_client.get_pr_diff(repo, pr_number)
    prompt = prompts.CODE_REVIEW_PROMPT.format(
        title=pr.get("title", ""),
        body=pr.get("body") or "",
        diff=diff,
    )
    raw = codex.run_codex(prompt, cwd=cwd, sandbox_mode="workspace-write")
    cleaned = _sanitize(raw, cwd)
    github_client.post_comment(repo, pr_number, prompts.with_bot_prefix(cleaned))
