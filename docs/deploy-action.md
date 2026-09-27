# Deploy action

`action.yml` is a composite action that applies Kubernetes manifests from a
caller's repository and waits for the rollout. Nine workflows pin it as
`relybytes/actions-kubernetes-deploy@v1`, so no input or output may change name
or meaning: new behaviour is added as an optional input with a safe default.

The input and output contract is documented in the top-level
[README](../README.md). This page covers how the steps work and why.

## Constraints the implementation is written against

- **Shared runners.** Most callers run on persistent self-hosted runners where
  jobs of different repositories execute concurrently as the same user, sharing
  `$HOME`, `/tmp`, `/usr/local/bin` and the process table. Six of the eight
  callers have no concurrency group, so two runs of the same namespace can
  overlap.
- **Hosted runners too.** The same file must work on `ubuntu-latest`.
- **No sudo, nothing machine-wide.** Missing tools are installed into a unique
  directory under `$RUNNER_TEMP` and published through `$GITHUB_PATH`.
- **No secret in `argv`.** Any job can read `/proc/<pid>/cmdline` of any other
  job of the same user.

## Step by step

| Step | What it does |
| --- | --- |
| Validate inputs | Shape checks, and the combinations that cannot work (`kustomize` with `replacements` or `env_substitution`) fail here rather than being ignored |
| Install kubectl | Reuses a `kubectl` that actually runs; otherwise downloads the build for `uname -s`/`uname -m` with `curl -fsSL --retry 3`, runs it before trusting it, and puts it on `$GITHUB_PATH` from a per-job directory |
| Ensure envsubst | Only when `env_substitution` is on and `kustomize` is off. Uses `envsubst` if installed, otherwise writes a python3 stand-in with the same semantics to a per-job directory. No package installation |
| Configure kubeconfig | Writes the raw or base64 kubeconfig to a `0600` file under `$RUNNER_TEMP`, masks the credential fields it finds inside, exports `KUBECONFIG`, and fails with the real cause when there is no current context |
| Ensure namespace | Creates the namespace with `create --dry-run=client -o yaml \| apply -f -` when `create_namespace` is true, so a concurrent run cannot lose the race. Otherwise checks access with `kubectl auth can-i` and reports kubectl's own stderr on failure |
| Create or update registry pull secret | Builds the `dockerconfigjson` with `jq` (or `python3`) from environment values and pipes a `Secret` into `kubectl apply -f -` |
| Prepare manifests | Copies every input path into its own numbered subdirectory of a `0700` work directory under `$RUNNER_TEMP`, then applies the placeholder replacements and `envsubst` to the copies |
| Apply manifests | One `kubectl apply` per file normally; a single invocation with a repeated `-f` when `prune` is on. Writes `applied_resources` and `deployment_time` |
| Update images | `kubectl set image` for each `set_image` entry |
| Wait for rollout | Always runs and always writes `rollout_status`; decides internally whether to wait |
| Cleanup | `if: always()`. Deletes the kubeconfig and the work directory, and clears `KUBECONFIG` |

## Decisions that are not obvious

- **Prune needs one invocation.** `--prune` deletes everything matching the
  selector that is not part of the set applied by the same command. Applying file
  by file with prune enabled makes each file delete the resources of the previous
  ones, and the deploy still reports success.
- **Placeholder keys are escaped as a basic regular expression**, with a `\001`
  delimiter for the `s///` command. `|` is left unescaped on purpose: it is
  literal in a BRE, and `\|` would become GNU alternation. The replacement value
  keeps its own escaping for `/`, `&` and `|`.
- **No `xargs` for trimming.** `xargs` applies shell quote processing: it eats
  backslashes, strips quotes, and exits 1 on an unmatched apostrophe. Trimming
  uses bash parameter expansion, which also removes a stray carriage return.
- **`applied_resources` keeps stderr out.** kubectl warnings go to the log only,
  the heredoc delimiter is random, and an empty result is written as an empty
  value.
- **`rollout_status` cannot be empty.** A skipped step produces no output, so the
  step runs unconditionally and returns `skipped` itself when `wait` is false,
  when `dry_run` is not `none`, or when nothing rollout-capable was applied. It
  is still empty if an earlier step fails, because the job stops there.
- **The rollout list comes from what this run applied**, not from the namespace.
  A manifest set with no deployment, statefulset or daemonset waits on nothing,
  even when `set_image` changed an image: pass `wait_resources` in that case.
- **`KUBECONFIG` is cleared in cleanup.** Deleting the file but leaving the
  variable set made later steps of the caller's job fail against
  `localhost:8080`, which says nothing about the cause.
- **The `kubectl` and `envsubst` directories are left in place** by cleanup: they
  are on `PATH` for the rest of the job and hold no secret. The runner removes
  `$RUNNER_TEMP` when the job ends.

## Testing locally

There is no cluster in CI, so the checks are static plus manual simulation.

Static, the same as CI:

```bash
python3 -m pip install pyyaml
python3 scripts/lint-steps.py action.yml
```

To exercise a step body by hand, extract it and run it with a fake `kubectl`
early on `PATH`:

```bash
python3 - <<'PY'
import pathlib, yaml
doc = yaml.safe_load(pathlib.Path("action.yml").read_text(encoding="utf-8"))
for i, step in enumerate(doc["runs"]["steps"], 1):
    if step.get("run"):
        pathlib.Path(f"/tmp/step-{i:02d}.bash").write_text(step["run"])
PY
```

Each step expects its own environment: the `env:` block of the step in
`action.yml`, plus `RUNNER_TEMP`, `GITHUB_OUTPUT`, `GITHUB_ENV` and
`GITHUB_PATH` pointing at writable paths. The steps that consume another step's
output (`WORK_DIR`, `APPLIED`, `KUBECONFIG_PATH`) take it from the environment as
well, so they can be run in isolation.

Behaviour worth re-checking after any change to the substitution code: a
placeholder key containing `.` or `|`, a value containing `/`, `&`, `|`, a quote
or a backslash, two input paths whose files have the same name, and a registry
password containing `"` and `\`.
