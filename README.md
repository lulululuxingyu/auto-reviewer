# Auto-Reviewer Agent

GitHub Actions agent that runs the local `codex` CLI against issues and pull requests, then posts the result back as a `🤖 Auto-Reviewer:` comment.

- Comment `@auto-code-review` on a pull request → code review comment.
- Comment `@auto-design-review` on an issue → design review comment.
- Or include the keyword in the issue/PR body at creation time.

## Architecture

- `.github/workflows/design-review.yml` — triggered by `issue_comment` or `issues.opened`.
- `.github/workflows/code-review.yml` — triggered by `issue_comment` or `pull_request.opened`.
- Both workflows run on a **self-hosted runner** that has access to the `codex` CLI.
- Python entrypoint: `python -m auto_reviewer {design|code} --repo OWNER/REPO --issue|--pr N`.
- Reviewer pipeline: prepare a worktree of the target repo → fetch issue/PR metadata + comments via `gh` CLI → render prompt → run `codex exec -C <worktree> --sandbox workspace-write` (codex can read source and run tests) → post comment via `gh`.

## Workspace layout

`auto-reviewer` keeps a persistent on-disk workspace per target repo so that codex
can run inside a real checkout and concurrent reviews don't fight:

```
$AUTO_REVIEWER_WORKSPACE/                       # default ./.workspace
└── <owner>__<repo>/
    ├── .git/                                    # the main shallow clone (default branch)
    └── .auto-reviewer/
        ├── lock                                 # flock; only held during fetch + worktree-add
        ├── pr-<N>/                              # git worktree for PR <N>
        ├── pr-<M>/                              # …another PR concurrently, no conflict
        └── issue-<N>/                           # worktree on the default branch for issue review
```

Override the root with `AUTO_REVIEWER_WORKSPACE=/path/to/cache`. In the deploy
templates below it's set to `$HOME/.cache/auto-reviewer` so the cache persists
across runs and isn't touched by `actions/checkout`'s clean step.

## Deploy on a fresh Mac

End-to-end checklist for taking a clean macOS box (Apple Silicon or Intel) to a working agent. **~30 minutes** if you already have GitHub access.

### 1. Install prerequisites

```bash
# Homebrew (skip if installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Tools the agent shells out to
brew install uv gh git

# OpenAI codex CLI
npm install -g @openai/codex
```

`uv` manages Python 3.11+ for you; no separate Python install needed.

### 2. Authenticate

```bash
# GitHub. Pick "Login with a web browser"; grant scopes 'repo' and 'workflow'.
gh auth login

# codex. Follow its prompt for ChatGPT / API key auth.
codex login
```

Sanity-check: `gh api user --jq .login` and `echo "ping" | codex exec --skip-git-repo-check --sandbox read-only -` should both succeed.

### 3. Install the agent on the runner machine

```bash
mkdir -p ~/Code && cd ~/Code
git clone https://github.com/lulululuxingyu/auto-reviewer.git
cd auto-reviewer
uv sync
uv run pytest         # optional: confirms the install
```

### 4. Register a self-hosted runner

Two options. Pick one.

**Per-repo runner** — simplest if you only auto-review one or two repos:

1. On GitHub → target repo → **Settings → Actions → Runners → New self-hosted runner → macOS / arm64** (or x64 on Intel).
2. In a fresh dir, paste the `mkdir`/`curl`/`tar`/`./config.sh` block GitHub shows you.
3. Install as a launchd LaunchAgent so it starts on login:
   ```bash
   ./svc.sh install
   ./svc.sh start
   ./svc.sh status
   ```

**Org-level runner** — preferred when you have several target repos:

1. On GitHub → org → **Settings → Actions → Runners → New runner**.
2. Same `config.sh`/`svc.sh` flow as above; one runner serves every repo in the org.

Notes:
- The runner runs in your **logged-in user session** (it's a LaunchAgent, not a LaunchDaemon). For an always-on box, enable auto-login: System Settings → Users & Groups → Login Options.
- If macOS quarantines the downloaded archive, run `xattr -dr com.apple.quarantine .` inside the runner dir before `./config.sh`.
- **Proxy**: The launchd service does NOT inherit shell environment variables. If your network requires a proxy, add `HTTP_PROXY` / `HTTPS_PROXY` to the workflow `env` block (see templates below).

### 5. Wire it up to a target repo

In **each** repo you want auto-reviewed, drop these two files into `.github/workflows/` and commit:

`.github/workflows/code-review.yml`:

```yaml
name: Code Review (auto-reviewer)

on:
  issue_comment:
    types: [created]
  pull_request:
    types: [opened]

permissions:
  pull-requests: write
  contents: read

concurrency:
  group: code-review-${{ github.event.issue.number || github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review-on-comment:
    if: >-
      github.event_name == 'issue_comment' &&
      github.event.issue.pull_request &&
      contains(github.event.comment.body, '@auto-code-review')
    runs-on: [self-hosted]
    steps:
      - name: Run code review
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # HTTP_PROXY: http://127.0.0.1:PORT   # uncomment if needed
          # HTTPS_PROXY: http://127.0.0.1:PORT
        run: |
          export AUTO_REVIEWER_WORKSPACE="$HOME/.cache/auto-reviewer"
          cd "$HOME/Code/auto-reviewer"
          git pull --ff-only || git pull --ff-only || echo "Warning: git pull failed, using local version"
          uv sync
          uv run python -m auto_reviewer code \
            --repo "${{ github.repository }}" \
            --pr "${{ github.event.issue.number }}"

  review-on-open:
    if: >-
      github.event_name == 'pull_request' &&
      contains(github.event.pull_request.body, '@auto-code-review')
    runs-on: [self-hosted]
    steps:
      - name: Run code review
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # HTTP_PROXY: http://127.0.0.1:PORT
          # HTTPS_PROXY: http://127.0.0.1:PORT
        run: |
          export AUTO_REVIEWER_WORKSPACE="$HOME/.cache/auto-reviewer"
          cd "$HOME/Code/auto-reviewer"
          git pull --ff-only || git pull --ff-only || echo "Warning: git pull failed, using local version"
          uv sync
          uv run python -m auto_reviewer code \
            --repo "${{ github.repository }}" \
            --pr "${{ github.event.pull_request.number }}"
```

`.github/workflows/design-review.yml`:

```yaml
name: Design Review (auto-reviewer)

on:
  issue_comment:
    types: [created]
  issues:
    types: [opened]

permissions:
  issues: write
  contents: read

concurrency:
  group: design-review-${{ github.event.issue.number }}
  cancel-in-progress: true

jobs:
  review-on-comment:
    if: >-
      github.event_name == 'issue_comment' &&
      !github.event.issue.pull_request &&
      contains(github.event.comment.body, '@auto-design-review')
    runs-on: [self-hosted]
    steps:
      - name: Run design review
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # HTTP_PROXY: http://127.0.0.1:PORT
          # HTTPS_PROXY: http://127.0.0.1:PORT
        run: |
          export AUTO_REVIEWER_WORKSPACE="$HOME/.cache/auto-reviewer"
          cd "$HOME/Code/auto-reviewer"
          git pull --ff-only || git pull --ff-only || echo "Warning: git pull failed, using local version"
          uv sync
          uv run python -m auto_reviewer design \
            --repo "${{ github.repository }}" \
            --issue "${{ github.event.issue.number }}"

  review-on-open:
    if: >-
      github.event_name == 'issues' &&
      contains(github.event.issue.body, '@auto-design-review')
    runs-on: [self-hosted]
    steps:
      - name: Run design review
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # HTTP_PROXY: http://127.0.0.1:PORT
          # HTTPS_PROXY: http://127.0.0.1:PORT
        run: |
          export AUTO_REVIEWER_WORKSPACE="$HOME/.cache/auto-reviewer"
          cd "$HOME/Code/auto-reviewer"
          git pull --ff-only || git pull --ff-only || echo "Warning: git pull failed, using local version"
          uv sync
          uv run python -m auto_reviewer design \
            --repo "${{ github.repository }}" \
            --issue "${{ github.event.issue.number }}"
```

Then go to that repo's **Settings → Actions → General → Workflow permissions** and confirm **"Read and write permissions"** is selected. Without this, `GITHUB_TOKEN` cannot post comments and the workflow will fail at the very last step.

### 6. Smoke-test

- Comment `@auto-code-review` on any PR → within ~30s the workflow appears under **Actions**; the review comment lands in 1–3 minutes.
- Comment `@auto-design-review` on any issue for design review.

If a run hangs in **Queued**, the runner isn't picking up the job — check `~/runners/<repo>/_diag/Runner_*.log` and `./svc.sh status`.

## codex contract

The agent invokes the codex CLI in non-interactive mode and reads the final assistant message from a temp file:

```
codex exec --skip-git-repo-check --sandbox <mode> --output-last-message <tmp> -
```

`<mode>` is `workspace-write` for real reviews (codex can read source and run tests inside the worktree) and `read-only` for stub/smoke runs.

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

- **Trigger keyword** for code review is `@auto-code-review` (in PR comment or body). For design review it's `@auto-design-review` (in issue comment or body). Edit the `contains()` condition in the workflow to change them.
- **Bot identity** is `github-actions[bot]` (uses the workflow's `GITHUB_TOKEN`). To use a custom bot account, replace `secrets.GITHUB_TOKEN` with a PAT secret in both workflows.
- **codex binary name** defaults to `codex`; override with the `CODEX_BIN` environment variable.
- **Proxy** for the self-hosted runner: uncomment and set `HTTP_PROXY` / `HTTPS_PROXY` in the workflow `env` block. The launchd service does not inherit shell environment variables.

## Layout

```
src/auto_reviewer/
  __main__.py        # CLI entry: design / code subcommands
  reviewers.py       # design_review() / code_review()
  codex.py           # subprocess wrapper for the codex CLI
  github_client.py   # gh CLI wrappers (fetch issue/PR, comments, diff, post comment)
  prompts.py         # prompt templates + 🤖 prefix helper
.github/workflows/
  design-review.yml
  code-review.yml
```
