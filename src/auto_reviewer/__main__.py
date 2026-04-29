import argparse
import sys

from auto_reviewer import reviewers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="auto_reviewer")
    sub = parser.add_subparsers(dest="command", required=True)

    design = sub.add_parser("design", help="Run a design review on an issue")
    design.add_argument("--repo", required=True, help="OWNER/REPO")
    design.add_argument("--issue", required=True, type=int)

    code = sub.add_parser("code", help="Run a code review on a pull request")
    code.add_argument("--repo", required=True, help="OWNER/REPO")
    code.add_argument("--pr", required=True, type=int)

    args = parser.parse_args(argv)

    if args.command == "design":
        reviewers.design_review(args.repo, args.issue)
    elif args.command == "code":
        reviewers.code_review(args.repo, args.pr)
    else:  # pragma: no cover - argparse enforces required subcommand
        parser.error(f"unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
