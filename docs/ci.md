# CI and releases

## Lint workflow

`.github/workflows/ci.yml` runs on every push to `main` and on every pull
request, on `ubuntu-latest`, with `contents: read`.

Three checks:

1. `pyyaml` is installed, then every YAML file in the repository that matters
   (`action.yml`, `examples/*.yml`, `.github/workflows/*.yml`) must parse.
2. `shellcheck` is used from the runner image, and installed with `apt-get` only
   if the image does not have it.
3. `scripts/lint-steps.py` shellchecks the `run` body of every composite step.

### scripts/lint-steps.py

The script loads `action.yml`, takes each composite step that has a `run`,
replaces every `${{ ... }}` expression with the placeholder word
`gha_expression` so the body is valid bash, writes it to a temporary file with a
`#!/usr/bin/env bash` shebang, and runs `shellcheck --shell=bash` on it. A step
whose `shell` is not `bash` is reported as a failure. The exit code is non-zero if
any step has a finding.

Usage:

```bash
python3 scripts/lint-steps.py [action.yml] [--shellcheck /path/to/shellcheck]
```

`--shellcheck` exists for machines where the binary is not called `shellcheck` on
`PATH`.

Findings are fixed in the action. If a finding is ever judged not worth fixing,
disable that one code with a `# shellcheck disable=SCxxxx` comment that says why,
next to the line. Never disable a whole file or a whole run.

## Releases

Callers pin `relybytes/actions-kubernetes-deploy@v1`, so a fix only reaches them
when the `v1` tag moves.

1. Merge to `main`.
2. Tag the commit `vX.Y.Z` and push the tag.
3. `.github/workflows/release.yml` triggers on `v*.*.*`, and force-moves the `vX`
   and `vX.Y` annotated tags to that commit. It needs `contents: write`.

Nothing else moves the aliases, and they are never expected to be moved by hand.
A tag that does not match `vX.Y.Z` fails the workflow instead of being guessed at.
