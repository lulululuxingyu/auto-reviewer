import json
import subprocess
import time


class GitHubError(RuntimeError):
    pass


_RETRYABLE_ERRORS = ("tls:", "connection reset", "ssl", "eof", "timeout")

# Max diff size in chars to pass to codex (~500KB, roughly 125K tokens)
MAX_DIFF_CHARS = 500_000


def _run(cmd: list[str], *, input_text: str | None = None, retries: int = 3) -> str:
    last_exc = None
    for attempt in range(retries):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                input=input_text,
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            err_msg = exc.stderr.strip().lower()
            if attempt < retries - 1 and any(e in err_msg for e in _RETRYABLE_ERRORS):
                last_exc = exc
                time.sleep(2 * (attempt + 1))
                continue
            raise GitHubError(
                f"{' '.join(cmd)} failed ({exc.returncode}): {exc.stderr.strip()}"
            ) from exc
        except FileNotFoundError as exc:
            raise GitHubError("gh CLI not found on PATH") from exc
    raise GitHubError(
        f"{' '.join(cmd)} failed after {retries} retries: {last_exc}"
    )


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

    Uses the 'List pull request files' API with manual pagination.
    Truncates output to MAX_DIFF_CHARS to avoid codex token limits.
    """
    all_files: list[dict] = []
    page = 1
    while True:
        out = _run([
            "gh", "api",
            f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}",
        ])
        files = json.loads(out)
        if not files:
            break
        all_files.extend(files)
        if len(files) < 100:
            break
        page += 1

    # Build file list summary
    file_list = "\n".join(
        f"  {f.get('status', '?'):10s} {f.get('filename', 'unknown')} (+{f.get('additions', 0)}/-{f.get('deletions', 0)})"
        for f in all_files
    )

    header = (
        f"# NOTE: This PR changes {len(all_files)} files — too many for a full diff.\n"
        f"# Patches are included below up to {MAX_DIFF_CHARS // 1000}KB. Truncated files\n"
        f"# are listed at the end. Use the working directory to inspect them directly.\n\n"
        f"## All changed files:\n{file_list}\n\n"
        f"## Patches (up to {MAX_DIFF_CHARS // 1000}KB):\n"
    )

    parts = [header]
    current_size = len(header)
    truncated_files = []

    for f in all_files:
        filename = f.get("filename", "unknown")
        patch = f.get("patch")
        if not patch:
            continue
        entry = f"--- a/{filename}\n+++ b/{filename}\n{patch}\n\n"
        if current_size + len(entry) > MAX_DIFF_CHARS:
            truncated_files.append(filename)
            continue
        parts.append(entry)
        current_size += len(entry)

    if truncated_files:
        parts.append(
            f"\n# {len(truncated_files)} file(s) truncated due to size limit.\n"
            f"# Use the working directory to review these files:\n"
        )
        for tf in truncated_files:
            parts.append(f"#   {tf}\n")

    return "".join(parts)


def _truncate_diff(diff: str) -> str:
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    truncated = diff[:MAX_DIFF_CHARS]
    # Cut at last complete file boundary
    last_diff_marker = truncated.rfind("\ndiff --git ")
    if last_diff_marker > MAX_DIFF_CHARS // 2:
        truncated = truncated[:last_diff_marker]
    return (
        truncated
        + f"\n\n# ... diff truncated at {MAX_DIFF_CHARS // 1000}KB."
        + " Use the working directory to review remaining files.\n"
    )


def get_pr_diff(repo: str, number: int) -> str:
    try:
        diff = _run(["gh", "pr", "diff", str(number), "--repo", repo])
        return _truncate_diff(diff)
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
