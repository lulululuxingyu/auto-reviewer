import fcntl
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path

from auto_reviewer import github_client


class WorkspaceError(RuntimeError):
    pass


def workspace_root() -> Path:
    return Path(os.environ.get("AUTO_REVIEWER_WORKSPACE", ".workspace")).resolve()


def repo_dir(repo: str) -> Path:
    owner, name = repo.split("/", 1)
    return workspace_root() / f"{owner}__{name}"


def _run(cmd: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise WorkspaceError(
            f"{' '.join(cmd)} failed ({exc.returncode}): {exc.stderr.strip()}"
        ) from exc
    except FileNotFoundError as exc:
        raise WorkspaceError(f"binary not found: {cmd[0]}") from exc
    return result.stdout


@contextmanager
def _repo_lock(repo: str):
    locks_dir = workspace_root() / ".locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    owner, name = repo.split("/", 1)
    lock_path = locks_dir / f"{owner}__{name}.lock"
    with open(lock_path, "w") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _ensure_clone(repo: str) -> Path:
    rd = repo_dir(repo)
    if (rd / ".git").exists():
        return rd
    rd.parent.mkdir(parents=True, exist_ok=True)
    _run(["gh", "repo", "clone", repo, str(rd), "--", "--depth", "50"])
    return rd


def _worktree_path(repo: str, slug: str) -> Path:
    return repo_dir(repo) / ".auto-reviewer" / slug


def _add_or_refresh_worktree(rd: Path, wt: Path, ref: str) -> None:
    if wt.exists():
        _run(["git", "reset", "--hard", ref], cwd=wt)
        _run(["git", "clean", "-fdx"], cwd=wt)
    else:
        wt.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "worktree", "add", "--detach", str(wt), ref], cwd=rd)


def prepare_pr_workspace(repo: str, pr_number: int) -> Path:
    with _repo_lock(repo):
        rd = _ensure_clone(repo)
        ref_local = f"refs/remotes/origin/pr-{pr_number}"
        _run(
            ["git", "fetch", "origin", f"+refs/pull/{pr_number}/head:{ref_local}"],
            cwd=rd,
        )
        wt = _worktree_path(repo, f"pr-{pr_number}")
        _add_or_refresh_worktree(rd, wt, f"origin/pr-{pr_number}")
        return wt


def prepare_issue_workspace(repo: str, issue_number: int) -> Path:
    with _repo_lock(repo):
        rd = _ensure_clone(repo)
        default_branch = github_client.get_default_branch(repo)
        _run(["git", "fetch", "origin", default_branch], cwd=rd)
        wt = _worktree_path(repo, f"issue-{issue_number}")
        _add_or_refresh_worktree(rd, wt, f"origin/{default_branch}")
        return wt
