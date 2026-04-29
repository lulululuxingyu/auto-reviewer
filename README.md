# Auto-Reviewer Agent

GitHub Actions agent that runs the local `codex` CLI against issues and pull requests, then posts the result back as a `🤖 Auto-Reviewer:` comment.

- Add the `design-needed` label to an issue → design review comment.
- Open or update a pull request → code review comment.

## Architecture

- `.github/workflows/design-review.yml` — triggered by `issues.labeled`.
- `.github/workflows/code-review.yml` — triggered by `pull_request` events.
- Both workflows run on a **self-hosted runner** that has access to the `codex` CLI.
- Python entrypoint: `python -m auto_reviewer {design|code} --repo OWNER/REPO --issue|--pr N`.
- Reviewer pipeline: fetch context via `gh` CLI → render prompt → run `codex` → post comment via `gh`.

## Self-hosted runner prerequisites

The runner machine must have the following on `PATH`:

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv)
- [`gh`](https://cli.github.com/) CLI (used for all GitHub API calls)
- `codex` CLI (the local LLM you want to use; see "codex contract" below)

## codex contract

The agent invokes the codex CLI in non-interactive mode and reads the final assistant message from a temp file:

```
codex exec --skip-git-repo-check --sandbox read-only --output-last-message <tmp> -
```

The prompt is piped to codex over stdin (no ARG_MAX limit).

For local smoke tests without a real codex binary, set both env vars to fall back to plain stdout capture:

```
CODEX_BIN=cat CODEX_NO_EXEC=1 uv run python -m auto_reviewer design --repo o/r --issue 1
```

(`cat` echoes the piped prompt as the "review", which is enough to verify the pipeline.)

## Local development

```bash
uv sync
uv run pytest
uv run python -m auto_reviewer --help
```

## Configuration knobs

- **Trigger label** for design review is hard-coded as `design-needed` in `design-review.yml`. Edit the `if:` condition to change it.
- **Bot identity** is `github-actions[bot]` (uses the workflow's `GITHUB_TOKEN`). To use a custom bot account, replace `secrets.GITHUB_TOKEN` with a PAT secret in both workflows.
- **codex binary name** defaults to `codex`; override with the `CODEX_BIN` environment variable.

## Layout

```
src/auto_reviewer/
  __main__.py        # CLI entry: design / code subcommands
  reviewers.py       # design_review() / code_review()
  codex.py           # subprocess wrapper for the codex CLI
  github_client.py   # gh CLI wrappers (fetch issue, PR diff, post comment)
  prompts.py         # prompt templates + 🤖 prefix helper
.github/workflows/
  design-review.yml
  code-review.yml
```
