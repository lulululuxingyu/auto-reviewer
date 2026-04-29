BOT_PREFIX = "🤖 Auto-Reviewer:"

DESIGN_REVIEW_PROMPT = """\
You are a senior engineer reviewing a design request from a GitHub issue.

Issue title:
{title}

Issue body:
{body}

Produce a design review with these sections (Markdown):
1. 问题理解
2. 方案选项（至少两种，附优缺点）
3. 推荐方案
4. 风险与缓解
"""

CODE_REVIEW_PROMPT = """\
You are a senior engineer reviewing a GitHub pull request.

PR title:
{title}

PR description:
{body}

Diff:
```diff
{diff}
```

Produce a code review with these sections (Markdown):
1. 摘要（这次变更做了什么）
2. 行级建议（引用文件/行号，给出可操作建议）
3. 阻塞问题（必须修复才能合并的，若无写"无"）
"""


def with_bot_prefix(body: str) -> str:
    return f"{BOT_PREFIX}\n\n{body}"
