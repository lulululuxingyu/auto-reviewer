from pathlib import Path

import pytest

from auto_reviewer import workspace


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_REVIEWER_WORKSPACE", str(tmp_path))
    return tmp_path


def test_repo_dir_uses_double_underscore(root):
    rd = workspace.repo_dir("foo/bar")
    assert rd == root / "foo__bar"


def test_workspace_root_default(monkeypatch, tmp_path):
    monkeypatch.delenv("AUTO_REVIEWER_WORKSPACE", raising=False)
    monkeypatch.chdir(tmp_path)
    assert workspace.workspace_root() == (tmp_path / ".workspace").resolve()


def test_prepare_pr_workspace_clones_then_adds_worktree(mocker, root):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((tuple(cmd), kwargs.get("cwd")))
        # Simulate clone creating .git so subsequent calls skip clone.
        if cmd[:3] == ["gh", "repo", "clone"]:
            target = Path(cmd[3])
            (target / ".git").mkdir(parents=True, exist_ok=True)
        return ""

    mocker.patch.object(workspace, "_run", side_effect=fake_run)
    wt = workspace.prepare_pr_workspace("foo/bar", 7)

    assert wt == root / "foo__bar" / ".auto-reviewer" / "pr-7"
    assert calls[0][0] == ("gh", "repo", "clone", "foo/bar", str(root / "foo__bar"), "--", "--depth", "50")
    fetch_call = next(c for c in calls if c[0][0] == "git" and c[0][1] == "fetch")
    assert fetch_call[0] == ("git", "fetch", "origin", "+refs/pull/7/head:refs/remotes/origin/pr-7")
    add_call = next(c for c in calls if c[0][:3] == ("git", "worktree", "add"))
    assert "origin/pr-7" in add_call[0]


def test_prepare_pr_workspace_refreshes_existing_worktree(mocker, root):
    rd = root / "foo__bar"
    wt = rd / ".auto-reviewer" / "pr-7"
    (rd / ".git").mkdir(parents=True)
    wt.mkdir(parents=True)

    calls = []
    mocker.patch.object(workspace, "_run", side_effect=lambda cmd, **k: calls.append((tuple(cmd), k.get("cwd"))) or "")

    workspace.prepare_pr_workspace("foo/bar", 7)

    cmds = [c[0] for c in calls]
    assert ("git", "fetch", "origin", "+refs/pull/7/head:refs/remotes/origin/pr-7") in cmds
    assert ("git", "reset", "--hard", "origin/pr-7") in cmds
    assert not any(c[:3] == ("git", "worktree", "add") for c in cmds)


def test_prepare_issue_workspace_uses_default_branch(mocker, root):
    (root / "foo__bar" / ".git").mkdir(parents=True)
    mocker.patch.object(workspace.github_client, "get_default_branch", return_value="trunk")
    calls = []
    mocker.patch.object(workspace, "_run", side_effect=lambda cmd, **k: calls.append((tuple(cmd), k.get("cwd"))) or "")

    wt = workspace.prepare_issue_workspace("foo/bar", 3)

    assert wt == root / "foo__bar" / ".auto-reviewer" / "issue-3"
    cmds = [c[0] for c in calls]
    assert ("git", "fetch", "origin", "trunk") in cmds
    assert any(c[:3] == ("git", "worktree", "add") and "origin/trunk" in c for c in cmds)
