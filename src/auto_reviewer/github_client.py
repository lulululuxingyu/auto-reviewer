import json
import subprocess


class GitHubError(RuntimeError):
    pass


def _run(cmd: list[str], *, input_text: str | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            input=input_text,
        )
    except subprocess.CalledProcessError as exc:
        raise GitHubError(
            f"{' '.join(cmd)} failed ({exc.returncode}): {exc.stderr.strip()}"
        ) from exc
    except FileNotFoundError as exc:
        raise GitHubError("gh CLI not found on PATH") from exc
    return result.stdout


def get_issue(repo: str, number: int) -> dict:
    out = _run(["gh", "api", f"/repos/{repo}/issues/{number}"])
    return json.loads(out)


def get_pr(repo: str, number: int) -> dict:
    out = _run(["gh", "api", f"/repos/{repo}/pulls/{number}"])
    return json.loads(out)


def get_comments(repo: str, number: int) -> list[dict]:
    out = _run(["gh", "api", f"/repos/{repo}/issues/{number}/comments", "--paginate"])
    comments = json.loads(out)
    return [
        {"user": c["user"]["login"], "body": c["body"]}
        for c in comments
        if not c["body"].strip().startswith("\U0001f916 Auto-Reviewer:")
    ]


def get_default_branch(repo: str) -> str:
    out = _run(["gh", "api", f"/repos/{repo}", "--jq", ".default_branch"])
    return out.strip()


def _get_pr_files_diff(repo: str, number: int) -> str:
    """Fallback when full diff exceeds GitHub's file limit.

    Uses the 'List pull request files' API to get per-file patches.
    """
    out = _run([
        "gh", "api", f"/repos/{repo}/pulls/{number}/files",
        "--paginate", "-q",
        '.[] | "--- a/" + .filename + "\\n+++ b/" + .filename + "\\n" + (.patch // "(binary or too large)")',
    ])
    header = (
        f"# NOTE: This PR has too many changed files for GitHub to return a full diff.\n"
        f"# The per-file patches below were obtained from the List PR Files API.\n"
        f"# Some files may show '(binary or too large)' if their individual patch\n"
        f"# is unavailable. Use the working directory to inspect those files directly.\n\n"
    )
    return header + out


def get_pr_diff(repo: str, number: int) -> str:
    try:
        return _run(["gh", "pr", "diff", str(number), "--repo", repo])
    except GitHubError as exc:
        if "too_large" in str(exc) or "406" in str(exc) or "exceeded" in str(exc):
            return _get_pr_files_diff(repo, number)
        raise


def post_comment(repo: str, number: int, body: str) -> None:
    _run(
        [
            "gh",
            "issue",
            "comment",
            str(number),
            "--repo",
            repo,
            "--body-file",
            "-",
        ],
        input_text=body,
    )
