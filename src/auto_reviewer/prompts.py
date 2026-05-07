BOT_PREFIX = "\U0001f916 Auto-Reviewer:"

_CITATION_RULES = """\
When you reference code, write it as `path/to/file.py:LINE` using paths relative to
the repository root. Do NOT use absolute filesystem paths and do NOT wrap citations
in Markdown links — the comment will be posted on github.com where local paths render
as broken links.
"""

_ONE_PASS_RULE = """\
CRITICAL: You MUST raise ALL issues in this single review. Do NOT hold back any
concerns for a future round. The developer should be able to address every issue
from this one review without needing another review cycle. Exhaustively check:
correctness, edge cases, error handling, security, naming, tests, and deployment
implications. If you are unsure whether something is an issue, include it with a
note that it may be a false positive — omitting it is worse than over-reporting.

If previous review comments exist in the discussion below, this is a re-review.
In a re-review, ONLY report:
1. Issues from prior review that remain unfixed
2. New issues introduced by the fixes themselves (regressions or conflicts)
Do NOT raise issues that existed in the original code but were not caught in prior
reviews — those were your responsibility to catch the first time. If all prior
issues have been addressed and the fixes introduced no new problems, respond with
"无" for blocking issues and note that prior feedback has been addressed.
"""

DESIGN_REVIEW_PROMPT = (
    """\
You are a senior engineer responding to a design request from a GitHub issue.

You are running inside a checkout of the repository's default branch. You can read
source files, run tests, and grep around to ground your design choices in the actual
codebase. Prefer concrete, code-backed reasoning over generic best practices.

"""
    + _CITATION_RULES
    + _ONE_PASS_RULE
    + """
Issue title:
{title}

Issue body:
{body}

Discussion (comments from participants):
{comments}

Produce a design review with these sections (Markdown):
1. 问题理解（结合实际代码现状）
2. 方案选项（至少两种，引用相关文件/函数说明影响范围）
3. 推荐方案
4. 风险与缓解
"""
)

CODE_REVIEW_PROMPT = (
    """\
You are a senior engineer reviewing a GitHub pull request.

You are running inside a checkout of this PR's HEAD. You can read any file, run
the test suite, or run static checks if you think it adds signal. Use the working
directory to verify claims rather than guessing from the diff alone.

"""
    + _CITATION_RULES
    + _ONE_PASS_RULE
    + """
PR title:
{title}

PR description:
{body}

Discussion (comments from participants):
{comments}

Diff (authoritative, from the GitHub API):
```diff
{diff}
```

Produce a code review with these sections (Markdown):
1. 摘要（这次变更做了什么）
2. 行级建议（引用文件/行号，给出可操作建议；可引用变更外的相关代码）
3. 阻塞问题（必须修复才能合并的，若无写"无"）
"""
)


def format_comments(comments: list[dict]) -> str:
    if not comments:
        return "(no comments)"
    parts = []
    for c in comments:
        parts.append(f"@{c['user']}:\n{c['body']}")
    return "\n\n---\n\n".join(parts)


def with_bot_prefix(body: str) -> str:
    return f"{BOT_PREFIX}\n\n{body}"
