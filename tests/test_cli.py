import pytest

from auto_reviewer import __main__ as cli


def test_cli_dispatches_design(mocker):
    fn = mocker.patch.object(cli.reviewers, "design_review")
    cli.main(["design", "--repo", "o/r", "--issue", "3"])
    fn.assert_called_once_with("o/r", 3)


def test_cli_dispatches_code(mocker):
    fn = mocker.patch.object(cli.reviewers, "code_review")
    cli.main(["code", "--repo", "o/r", "--pr", "11"])
    fn.assert_called_once_with("o/r", 11)


def test_cli_requires_subcommand():
    with pytest.raises(SystemExit):
        cli.main([])
