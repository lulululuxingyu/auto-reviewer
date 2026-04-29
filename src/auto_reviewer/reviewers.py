from auto_reviewer import codex, github_client, prompts


def design_review(repo: str, issue_number: int) -> None:
    issue = github_client.get_issue(repo, issue_number)
    prompt = prompts.DESIGN_REVIEW_PROMPT.format(
        title=issue.get("title", ""),
        body=issue.get("body") or "",
    )
    output = codex.run_codex(prompt)
    github_client.post_comment(repo, issue_number, prompts.with_bot_prefix(output))


def code_review(repo: str, pr_number: int) -> None:
    pr = github_client.get_issue(repo, pr_number)
    diff = github_client.get_pr_diff(repo, pr_number)
    prompt = prompts.CODE_REVIEW_PROMPT.format(
        title=pr.get("title", ""),
        body=pr.get("body") or "",
        diff=diff,
    )
    output = codex.run_codex(prompt)
    github_client.post_comment(repo, pr_number, prompts.with_bot_prefix(output))
