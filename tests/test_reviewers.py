from pathlib import Path

from auto_reviewer import reviewers


def test_sanitize_strips_workspace_prefix():
    cwd = Path("/abs/wt")
    out = reviewers._sanitize("see /abs/wt/calc.py:5 for details", cwd)
    assert out == "see calc.py:5 for details"


def test_sanitize_unwraps_local_markdown_links():
    cwd = Path("/abs/wt")
    text = "ref [calc.py:5](/abs/wt/calc.py:5) and [calc.py:6](calc.py:6)"
    out = reviewers._sanitize(text, cwd)
    assert out == "ref calc.py:5 and calc.py:6"


def test_sanitize_preserves_http_links():
    cwd = Path("/abs/wt")
    text = "see [docs](https://example.com/x) and [calc.py:5](/abs/wt/calc.py:5)"
    out = reviewers._sanitize(text, cwd)
    assert "[docs](https://example.com/x)" in out
    assert "[calc.py:5]" not in out
    assert "calc.py:5" in out


def test_design_review_pipeline(mocker, tmp_path):
    get_issue = mocker.patch.object(
        reviewers.github_client,
        "get_issue",
        return_value={"title": "T", "body": "B"},
    )
    mocker.patch.object(
        reviewers.github_client,
        "get_comments",
        return_value=[{"user": "alice", "body": "context here"}],
    )
    prep = mocker.patch.object(
        reviewers.workspace, "prepare_issue_workspace", return_value=tmp_path
    )
    run_codex = mocker.patch.object(
        reviewers.codex, "run_codex", return_value="codex-out"
    )
    post = mocker.patch.object(reviewers.github_client, "post_comment")

    reviewers.design_review("o/r", 5)

    get_issue.assert_called_once_with("o/r", 5)
    prep.assert_called_once_with("o/r", 5)
    sent_prompt = run_codex.call_args.args[0]
    assert "T" in sent_prompt and "B" in sent_prompt
    assert "@alice:" in sent_prompt
    assert "context here" in sent_prompt
    assert run_codex.call_args.kwargs["cwd"] == tmp_path
    assert run_codex.call_args.kwargs["sandbox_mode"] == "workspace-write"
    body = post.call_args.args[2]
    assert body.startswith("\U0001f916 Auto-Reviewer:")
    assert "codex-out" in body


def test_code_review_pipeline(mocker, tmp_path):
    get_pr = mocker.patch.object(
        reviewers.github_client,
        "get_pr",
        return_value={"title": "PR", "body": "desc"},
    )
    mocker.patch.object(
        reviewers.github_client,
        "get_comments",
        return_value=[],
    )
    mocker.patch.object(
        reviewers.github_client, "get_pr_diff", return_value="--- a\n+++ b\n"
    )
    prep = mocker.patch.object(
        reviewers.workspace, "prepare_pr_workspace", return_value=tmp_path
    )
    run_codex = mocker.patch.object(
        reviewers.codex, "run_codex", return_value="lgtm"
    )
    post = mocker.patch.object(reviewers.github_client, "post_comment")

    reviewers.code_review("o/r", 9)

    get_pr.assert_called_once_with("o/r", 9)
    prep.assert_called_once_with("o/r", 9)
    sent_prompt = run_codex.call_args.args[0]
    assert "PR" in sent_prompt
    assert "desc" in sent_prompt
    assert "--- a" in sent_prompt
    assert "(no comments)" in sent_prompt
    assert run_codex.call_args.kwargs["cwd"] == tmp_path
    assert run_codex.call_args.kwargs["sandbox_mode"] == "workspace-write"
    body = post.call_args.args[2]
    assert body.startswith("\U0001f916 Auto-Reviewer:")
    assert "lgtm" in body


def test_design_review_handles_null_body(mocker, tmp_path):
    mocker.patch.object(
        reviewers.github_client,
        "get_issue",
        return_value={"title": "T", "body": None},
    )
    mocker.patch.object(
        reviewers.github_client,
        "get_comments",
        return_value=[],
    )
    mocker.patch.object(
        reviewers.workspace, "prepare_issue_workspace", return_value=tmp_path
    )
    run_codex = mocker.patch.object(reviewers.codex, "run_codex", return_value="x")
    mocker.patch.object(reviewers.github_client, "post_comment")

    reviewers.design_review("o/r", 1)

    assert "T" in run_codex.call_args.args[0]
