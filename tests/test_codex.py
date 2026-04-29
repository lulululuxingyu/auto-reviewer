import subprocess

import pytest

from auto_reviewer import codex


def test_run_codex_returns_last_message(mocker):
    written = {}

    def fake_run(cmd, **kwargs):
        idx = cmd.index("--output-last-message")
        out_path = cmd[idx + 1]
        with open(out_path, "w") as f:
            f.write("final-reply\n")
        written["cmd"] = cmd
        written["input"] = kwargs.get("input")
        written["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="noisy progress\n", stderr=""
        )

    mocker.patch.object(codex.subprocess, "run", side_effect=fake_run)
    out = codex.run_codex("hello prompt")
    assert out == "final-reply\n"

    cmd = written["cmd"]
    assert cmd[0] == "codex"
    assert cmd[1] == "exec"
    assert "--skip-git-repo-check" in cmd
    assert cmd[cmd.index("--sandbox") + 1] == "read-only"
    assert cmd[-1] == "-"
    assert written["input"] == "hello prompt"
    assert written["cwd"] is None


def test_run_codex_passes_cwd_and_sandbox_mode(mocker, tmp_path):
    written = {}

    def fake_run(cmd, **kwargs):
        idx = cmd.index("--output-last-message")
        with open(cmd[idx + 1], "w") as f:
            f.write("ok")
        written["cmd"] = cmd
        written["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )

    mocker.patch.object(codex.subprocess, "run", side_effect=fake_run)
    codex.run_codex("p", cwd=tmp_path, sandbox_mode="workspace-write")
    assert written["cwd"] == str(tmp_path)
    assert written["cmd"][written["cmd"].index("--sandbox") + 1] == "workspace-write"


def test_run_codex_respects_codex_bin_env(mocker, monkeypatch):
    monkeypatch.setenv("CODEX_BIN", "echo")
    monkeypatch.setenv("CODEX_NO_EXEC", "1")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="echoed\n", stderr=""
        )

    mocker.patch.object(codex.subprocess, "run", side_effect=fake_run)
    out = codex.run_codex("hi")
    assert out == "echoed\n"
    assert captured["cmd"] == ["echo"]
    assert captured["input"] == "hi"


def test_run_codex_raises_on_timeout(mocker):
    mocker.patch.object(
        codex.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=1),
    )
    with pytest.raises(codex.CodexError, match="timed out"):
        codex.run_codex("hi", timeout=1)


def test_run_codex_raises_on_nonzero_exit(mocker):
    mocker.patch.object(
        codex.subprocess,
        "run",
        side_effect=subprocess.CalledProcessError(
            returncode=2, cmd=["codex"], stderr="boom"
        ),
    )
    with pytest.raises(codex.CodexError, match="exited with 2.*boom"):
        codex.run_codex("hi")


def test_run_codex_raises_when_binary_missing(mocker):
    mocker.patch.object(codex.subprocess, "run", side_effect=FileNotFoundError())
    with pytest.raises(codex.CodexError, match="not found"):
        codex.run_codex("hi")
