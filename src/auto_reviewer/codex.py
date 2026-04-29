import os
import subprocess
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 600


class CodexError(RuntimeError):
    pass


def run_codex(prompt: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
    binary = os.environ.get("CODEX_BIN", "codex")
    use_exec = os.environ.get("CODEX_NO_EXEC") != "1"

    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as tmp:
        out_path = Path(tmp.name)

    try:
        cmd = [binary]
        if use_exec:
            cmd += [
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--output-last-message",
                str(out_path),
                "-",  # read prompt from stdin
            ]
        else:
            # Test/stub mode: pipe prompt to stdin, capture stdout as the result.
            pass

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexError(f"codex timed out after {timeout}s") from exc
        except subprocess.CalledProcessError as exc:
            raise CodexError(
                f"codex exited with {exc.returncode}: {exc.stderr.strip()}"
            ) from exc
        except FileNotFoundError as exc:
            raise CodexError(f"codex binary not found: {binary}") from exc

        if use_exec:
            return out_path.read_text()
        return result.stdout
    finally:
        out_path.unlink(missing_ok=True)
