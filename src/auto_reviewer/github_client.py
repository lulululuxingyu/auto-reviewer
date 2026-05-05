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


def get_pr_diff(repo: str, number: int) -> str:
    return _run(["gh", "pr", "diff", str(number), "--repo", repo])


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
