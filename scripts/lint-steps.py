#!/usr/bin/env python3
"""Run shellcheck over every run script of a composite GitHub Action.

The step bodies are plain bash, so shellcheck can check them, but they may hold
GitHub Actions expressions (``${{ ... }}``) which are not shell syntax. Every
expression is therefore replaced by a harmless placeholder word before the body
is written to a temporary file with a bash shebang and handed to shellcheck.

Usage:
    python3 scripts/lint-steps.py [action.yml] [--shellcheck /path/to/shellcheck]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

# Non-greedy and DOTALL, so a multi-line expression is replaced as one unit.
EXPRESSION = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)

# A bare word: it is valid shell in every position an expression can appear in,
# quoted or not, so the replacement never changes how the script parses.
PLACEHOLDER = "gha_expression"


def slugify(name: str) -> str:
    """Turn a step name into something usable as a file name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "step"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shellcheck every run script of a composite action",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="action.yml",
        type=pathlib.Path,
        help="path to the composite action definition (default: action.yml)",
    )
    parser.add_argument(
        "--shellcheck",
        default="shellcheck",
        help="shellcheck executable to use (default: shellcheck on PATH)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    shellcheck = shutil.which(args.shellcheck)
    if shellcheck is None:
        print(f"shellcheck not found: {args.shellcheck}", file=sys.stderr)
        return 1

    try:
        document = yaml.safe_load(args.action.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        print(f"{args.action} is not valid YAML: {error}", file=sys.stderr)
        return 1

    steps = ((document or {}).get("runs") or {}).get("steps") or []
    if not steps:
        print(f"{args.action} declares no composite step", file=sys.stderr)
        return 1

    checked = 0
    failed = 0

    with tempfile.TemporaryDirectory(prefix="lint-steps-") as workdir:
        for position, step in enumerate(steps, start=1):
            script = step.get("run")
            if not script:
                continue

            name = step.get("name") or f"step {position}"
            shell = step.get("shell")
            if shell != "bash":
                print(f"FAIL {name}: shell is {shell!r}, expected 'bash'")
                failed += 1
                continue

            body = EXPRESSION.sub(PLACEHOLDER, script)
            path = pathlib.Path(workdir) / f"{position:02d}-{slugify(name)}.bash"
            # newline="\n": on a Windows checkout the default translation would
            # add carriage returns that shellcheck then reports as SC1017.
            path.write_text(
                f"#!/usr/bin/env bash\n{body}",
                encoding="utf-8",
                newline="\n",
            )

            result = subprocess.run(
                [shellcheck, "--shell=bash", "--color=never", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            checked += 1

            if result.returncode == 0:
                print(f"ok   {name}")
                continue

            failed += 1
            print(f"FAIL {name}")
            output = (result.stdout + result.stderr).rstrip()
            if output:
                print(output)

    print(f"\n{checked} step(s) checked, {failed} with findings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
