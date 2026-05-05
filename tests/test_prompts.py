from auto_reviewer import prompts


def test_design_prompt_substitutes_fields():
    rendered = prompts.DESIGN_REVIEW_PROMPT.format(
        title="Add caching", body="We need cache.", comments="(no comments)"
    )
    assert "Add caching" in rendered
    assert "We need cache." in rendered
    assert "推荐方案" in rendered


def test_code_prompt_substitutes_fields():
    rendered = prompts.CODE_REVIEW_PROMPT.format(
        title="Fix bug", body="Closes #1", diff="--- a\n+++ b\n", comments="(no comments)"
    )
    assert "Fix bug" in rendered
    assert "Closes #1" in rendered
    assert "--- a" in rendered
    assert "阻塞问题" in rendered


def test_format_comments_empty():
    assert prompts.format_comments([]) == "(no comments)"


def test_format_comments_with_entries():
    comments = [
        {"user": "alice", "body": "looks good"},
        {"user": "bob", "body": "needs fix"},
    ]
    out = prompts.format_comments(comments)
    assert "@alice:" in out
    assert "looks good" in out
    assert "@bob:" in out
    assert "needs fix" in out


def test_with_bot_prefix():
    out = prompts.with_bot_prefix("hello")
    assert out.startswith("\U0001f916 Auto-Reviewer:")
    assert out.endswith("hello")
