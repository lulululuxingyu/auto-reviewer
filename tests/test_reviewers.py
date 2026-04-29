from auto_reviewer import reviewers


def test_design_review_pipeline(mocker):
    get_issue = mocker.patch.object(
        reviewers.github_client,
        "get_issue",
        return_value={"title": "T", "body": "B"},
    )
    run_codex = mocker.patch.object(
        reviewers.codex, "run_codex", return_value="codex-out"
    )
    post = mocker.patch.object(reviewers.github_client, "post_comment")

    reviewers.design_review("o/r", 5)

    get_issue.assert_called_once_with("o/r", 5)
    sent_prompt = run_codex.call_args.args[0]
    assert "T" in sent_prompt and "B" in sent_prompt
    body = post.call_args.args[2]
    assert body.startswith("🤖 Auto-Reviewer:")
    assert "codex-out" in body


def test_code_review_pipeline(mocker):
    mocker.patch.object(
        reviewers.github_client,
        "get_issue",
        return_value={"title": "PR", "body": "desc"},
    )
    mocker.patch.object(
        reviewers.github_client, "get_pr_diff", return_value="--- a\n+++ b\n"
    )
    run_codex = mocker.patch.object(
        reviewers.codex, "run_codex", return_value="lgtm"
    )
    post = mocker.patch.object(reviewers.github_client, "post_comment")

    reviewers.code_review("o/r", 9)

    sent_prompt = run_codex.call_args.args[0]
    assert "PR" in sent_prompt
    assert "desc" in sent_prompt
    assert "--- a" in sent_prompt
    body = post.call_args.args[2]
    assert body.startswith("🤖 Auto-Reviewer:")
    assert "lgtm" in body


def test_design_review_handles_null_body(mocker):
    mocker.patch.object(
        reviewers.github_client,
        "get_issue",
        return_value={"title": "T", "body": None},
    )
    run_codex = mocker.patch.object(reviewers.codex, "run_codex", return_value="x")
    mocker.patch.object(reviewers.github_client, "post_comment")

    reviewers.design_review("o/r", 1)

    # Should render without crashing and substitute empty body.
    assert "T" in run_codex.call_args.args[0]
