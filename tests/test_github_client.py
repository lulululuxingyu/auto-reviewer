import json
import subprocess

import pytest

from auto_reviewer import github_client


def _completed(stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_get_issue_parses_json(mocker):
    payload = {"number": 7, "title": "t", "body": "b"}
    mock_run = mocker.patch.object(
        github_client.subprocess, "run", return_value=_completed(json.dumps(payload))
    )
    result = github_client.get_issue("o/r", 7)
    assert result == payload
    assert mock_run.call_args.args[0] == ["gh", "api", "/repos/o/r/issues/7"]


def test_get_pr_parses_json(mocker):
    payload = {"number": 9, "title": "pr-title", "body": "pr-body"}
    mock_run = mocker.patch.object(
        github_client.subprocess, "run", return_value=_completed(json.dumps(payload))
    )
    result = github_client.get_pr("o/r", 9)
    assert result == payload
    assert mock_run.call_args.args[0] == ["gh", "api", "/repos/o/r/pulls/9"]


def test_get_pr_diff_returns_stdout(mocker):
    mock_run = mocker.patch.object(
        github_client.subprocess, "run", return_value=_completed("--- a\n+++ b\n")
    )
    out = github_client.get_pr_diff("o/r", 9)
    assert out.startswith("--- a")
    assert mock_run.call_args.args[0] == ["gh", "pr", "diff", "9", "--repo", "o/r"]


def test_post_comment_passes_body_via_stdin(mocker):
    mock_run = mocker.patch.object(
        github_client.subprocess, "run", return_value=_completed("")
    )
    github_client.post_comment("o/r", 12, "hello")
    cmd = mock_run.call_args.args[0]
    assert cmd == ["gh", "issue", "comment", "12", "--repo", "o/r", "--body-file", "-"]
    assert mock_run.call_args.kwargs["input"] == "hello"


def test_run_propagates_gh_failure(mocker):
    mocker.patch.object(
        github_client.subprocess,
        "run",
        side_effect=subprocess.CalledProcessError(returncode=1, cmd=["gh"], stderr="bad"),
    )
    with pytest.raises(github_client.GitHubError, match="bad"):
        github_client.get_issue("o/r", 1)


def test_run_raises_when_gh_missing(mocker):
    mocker.patch.object(github_client.subprocess, "run", side_effect=FileNotFoundError())
    with pytest.raises(github_client.GitHubError, match="gh CLI not found"):
        github_client.get_issue("o/r", 1)
