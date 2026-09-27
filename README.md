# Kubernetes Deploy by RelyBytes

Deploy services to a Kubernetes cluster by applying YAML manifests, with namespace management, recursive manifest discovery, placeholder replacements, optional private registry pull secret creation, image updates, dry-run support, pruning, and rollout management.

The action is built for shared self-hosted Linux runners, where jobs from several repositories run concurrently as the same user, and works unchanged on GitHub-hosted runners such as `ubuntu-latest`.

## Features

- Configure Kubernetes access from a raw or base64-encoded kubeconfig, in a file private to the run
- Select the kubeconfig context
- Create the namespace if it is missing, idempotently, or check access to an existing one
- Apply YAML/JSON manifests from files or directories, discovered recursively
- Support Kustomize with `kubectl apply -k`
- Replace placeholders before the deploy
- Run `envsubst` on the manifests, with a python3 stand-in when `envsubst` is not installed
- Optionally create or update an `imagePullSecret` for private registries, without the password ever reaching a command line
- Update container images with `kubectl set image`
- Support client and server dry-run
- Optional `kubectl --prune`, applied in a single invocation so pruning cannot delete what the same run created
- Wait for deployment, statefulset, and daemonset rollouts
- Output the applied resources, the rollout status, and the deployment timestamp

## Usage

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches:
      - main

# One deploy at a time per environment. The action makes its own cluster
# operations idempotent, but it cannot order two runs that apply different
# commits to the same namespace.
concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: [self-hosted, linux]

    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Deploy to Kubernetes
        uses: relybytes/actions-kubernetes-deploy@v1
        with:
          kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
          namespace: production
          create_namespace: "false"
          manifests: ./k8s
          replacements: |
            __IMAGE__=ghcr.io/myorg/api:${{ github.sha }}
            __APP_ENV__=production
          wait: "true"
          wait_timeout: "300s"
```

On GitHub-hosted runners the only difference is the `runs-on` line:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
```

## Usage with a private registry

Use this when your Kubernetes cluster needs to pull images from a private registry such as GHCR, Harbor, Docker Hub private repositories, or OVHcloud Managed Private Registry.

```yaml
- name: Deploy to Kubernetes
  uses: relybytes/actions-kubernetes-deploy@v1
  with:
    kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
    namespace: production
    create_namespace: "false"

    create_registry_secret: "true"
    registry_server: registry.example.com
    registry_username: ${{ secrets.DOCKER_REGISTRY_USERNAME }}
    registry_password: ${{ secrets.DOCKER_REGISTRY_PASSWORD }}
    registry_email: devops@example.com
    registry_secret_name: registry-pull-secret

    manifests: ./k8s
    replacements: |
      __IMAGE__=registry.example.com/my-project/my-app:${{ github.sha }}
      __APP_ENV__=production
      __REGISTRY_SECRET__=registry-pull-secret

    wait: "true"
    wait_timeout: "300s"
```

Your Kubernetes `Deployment` should reference the pull secret:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      imagePullSecrets:
        - name: __REGISTRY_SECRET__
      containers:
        - name: app
          image: __IMAGE__
```

## Usage with OVHcloud Managed Private Registry

```yaml
- name: Deploy to Kubernetes
  uses: relybytes/actions-kubernetes-deploy@v1
  with:
    kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
    namespace: vulneralytics
    create_namespace: "false"

    create_registry_secret: "true"
    registry_server: u38z470p.gra7.container-registry.ovh.net
    registry_username: ${{ secrets.DOCKER_REGISTRY_USERNAME }}
    registry_password: ${{ secrets.DOCKER_REGISTRY_PASSWORD }}
    registry_email: devops@relybytes.com
    registry_secret_name: harbor-pull-secret

    manifests: ./k8s/prod
    replacements: |
      __IMAGE__=u38z470p.gra7.container-registry.ovh.net/vulneralytics/cyberitatech/frontend-prod:${{ github.sha }}
      __APP_ENV__=production
      __REGISTRY_SECRET__=harbor-pull-secret

    wait: "true"
    wait_timeout: "300s"
```

## Usage with Kustomize

`kustomize: "true"` hands the path straight to `kubectl apply -k`, so the manifests are rendered by kustomize and not by this action. `replacements` and `env_substitution` are therefore rejected with an error instead of being silently ignored: use a kustomize image or configMap generator for those values.

```yaml
- name: Deploy with Kustomize
  uses: relybytes/actions-kubernetes-deploy@v1
  with:
    kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
    namespace: production
    create_namespace: "false"
    manifests: ./k8s/overlays/production
    kustomize: "true"
```

## Usage with `kubectl set image`

```yaml
- name: Deploy and update images
  uses: relybytes/actions-kubernetes-deploy@v1
  with:
    kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
    namespace: production
    create_namespace: "false"
    manifests: ./k8s
    set_image: |
      deployment/api=app=ghcr.io/myorg/api:${{ github.sha }}
      deployment/worker=worker=ghcr.io/myorg/worker:${{ github.sha }}
    wait_resources: |
      deployment/api
      deployment/worker
```

`wait_resources` is listed explicitly here because the rollout wait is built from what the apply step reported. A manifest set that contains no deployment, statefulset, or daemonset waits on nothing, even when `set_image` changed an image.

## Inputs

| Input                    | Required | Default                | Description                                                                                                                              |
| ------------------------ | -------: | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `kubeconfig`             |      yes |                        | Kubeconfig content, raw YAML or base64-encoded                                                                                           |
| `context`                |       no | `""`                   | Kubeconfig context to use. When empty the kubeconfig must set `current-context`                                                           |
| `namespace`              |      yes |                        | Target Kubernetes namespace                                                                                                              |
| `create_namespace`       |       no | `true`                 | Create the namespace if it is missing. Needs cluster-scoped rights on namespaces, so set it to `"false"` with namespace-scoped credentials |
| `manifests`              |      yes |                        | Manifest file, directory, or several paths. Directories are scanned recursively for `.yaml`, `.yml`, and `.json` files                    |
| `kustomize`              |       no | `false`                | Apply manifests using `kubectl apply -k`. Cannot be combined with `replacements` or `env_substitution`                                    |
| `replacements`           |       no | `""`                   | Newline-separated `KEY=VALUE` placeholder replacements, applied literally                                                                 |
| `set_image`              |       no | `""`                   | Newline-separated `resource=container=image` entries                                                                                      |
| `env_substitution`       |       no | `false`                | Apply `envsubst` to the manifests. Cannot be combined with `kustomize`                                                                   |
| `validate`               |       no | `true`                 | Run `kubectl apply` with validation                                                                                                      |
| `dry_run`                |       no | `none`                 | Dry-run mode: `none`, `client`, or `server`                                                                                               |
| `prune`                  |       no | `false`                | Enable `kubectl --prune`. Every manifest is then applied in a single `kubectl apply` invocation                                           |
| `prune_label`            |       no | `""`                   | Label selector, required when prune is enabled                                                                                           |
| `wait`                   |       no | `true`                 | Wait for the rollout after apply                                                                                                         |
| `wait_resources`         |       no | `""`                   | Resources to wait on. When empty, the rollout-capable resources this run applied                                                          |
| `wait_timeout`           |       no | `300s`                 | Rollout wait timeout                                                                                                                     |
| `kubectl_version`        |       no | `""`                   | kubectl version to install, for example `v1.30.0`. Empty reuses a working kubectl, or installs the current stable one                     |
| `create_registry_secret` |       no | `false`                | Create or update a Kubernetes `imagePullSecret` for private registries                                                                    |
| `registry_server`        |       no | `""`                   | Container registry server, for example `ghcr.io`, `registry.example.com`, or a Harbor or OVH registry URL                                |
| `registry_username`      |       no | `""`                   | Container registry username                                                                                                              |
| `registry_password`      |       no | `""`                   | Container registry password or token                                                                                                      |
| `registry_email`         |       no | `devops@relybytes.com` | Container registry email                                                                                                                 |
| `registry_secret_name`   |       no | `""`                   | Kubernetes `imagePullSecret` name to create or update                                                                                     |

## Outputs

| Output              | Description                                                                                                                        |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `applied_resources` | Resources applied to the cluster, one per line, empty when nothing was applied. kubectl warnings stay in the log and out of this value |
| `rollout_status`    | Always one of `success`, `failed`, or `skipped`. `skipped` when `wait` is false, when `dry_run` is not `none`, or when nothing rollout-capable was applied |
| `deployment_time`   | UTC deployment timestamp                                                                                                           |

## Runner requirements

The action never uses `sudo` and never writes outside `$RUNNER_TEMP`. What it cannot find, it installs into a directory of its own for that job and adds to `$GITHUB_PATH`.

On GitHub-hosted runners (`ubuntu-latest` and equivalents), everything is already there:

- `bash`, `curl`, `sed`, `find`, `base64`
- `kubectl` is installed by the action if missing, or when `kubectl_version` pins a version
- `jq`, used for the registry pull secret
- `python3`, used as the fallback for the registry secret and for `envsubst`

On self-hosted runners the following must be present:

- `bash` 4.4 or newer, `curl`, `sed`, `find`, `base64`, `mktemp`
- `jq` or `python3`, only when `create_registry_secret` is `"true"`
- `envsubst` (package `gettext-base`) or `python3`, only when `env_substitution` is `"true"`
- outbound access to `dl.k8s.io`, only when `kubectl` is missing or a version is pinned

What the action installs by itself, per job, under `$RUNNER_TEMP`:

- `kubectl`, for the operating system and architecture reported by `uname`, verified by running it before use
- a small `envsubst` stand-in written in python3, when `envsubst` is not installed

If a prerequisite is genuinely missing the step fails immediately naming it, rather than failing later with a confusing error.

## Shared self-hosted runners

Several callers of this action run on persistent runners shared by jobs of different repositories, executing as the same user. The action is written for that:

- the kubeconfig, the rendered manifests, and every temporary file live in a uniquely named path under `$RUNNER_TEMP`, with `0600` files and `0700` directories, never in `$HOME/.kube/config`, never in `/tmp`, and never in the checked-out workspace
- `kubectl` and the `envsubst` stand-in are installed per job and prepended to `$GITHUB_PATH`, so a broken or replaced binary cannot affect the other jobs on the machine, and nothing machine-wide is written
- no credential is ever passed as a command-line argument, because any process table entry on the runner is readable by every other job of the same user
- the decoded kubeconfig credentials and the generated `dockerconfigjson` are passed to `::add-mask::`, so they stay out of the log even if a later command prints them
- namespace creation and the pull secret both go through `create --dry-run=client -o yaml | kubectl apply -f -`, so two concurrent runs targeting the same namespace cannot fail each other
- the cleanup step deletes only the paths this run created under `$RUNNER_TEMP`, and is safe to run twice or after a step that never ran

Residual risk that cannot be fixed from inside the action: on a self-hosted runner where every job runs as the same operating-system user, that user can read the environment and the files of the jobs running next to it, this action's `$RUNNER_TEMP` included. File permissions and keeping secrets off command lines raise the bar, they do not isolate. Strong isolation needs ephemeral runners, or at least one runner per repository, with the runner process for each job started as its own user.

### The action leaves no usable KUBECONFIG

The cleanup step deletes the kubeconfig file and clears the `KUBECONFIG` variable it exported. Steps of your job that run after this action therefore have no cluster credentials: if a later step needs `kubectl`, give it its own kubeconfig, or use the action again. The `kubectl` binary the action may have installed stays on `PATH` for the rest of the job.

## Manifest placeholders

You can define placeholders in your Kubernetes manifests and replace them at deploy time.

Example workflow:

```yaml
replacements: |
  __IMAGE__=ghcr.io/myorg/api:${{ github.sha }}
  __VERSION__=${{ github.sha }}
  __APP_ENV__=production
  __REGISTRY_SECRET__=registry-pull-secret
```

Example manifest:

```yaml
containers:
  - name: app
    image: __IMAGE__
```

Keys are matched literally, so a key containing `.`, `*`, or `|` replaces only the exact text. The manifests are copied to a private directory before anything is substituted, each input path into its own numbered subdirectory, so the checkout is never modified and two inputs with the same file name cannot collide.

## Private registry pull secrets

When `create_registry_secret` is `"true"`, the action builds the `dockerconfigjson` with `jq`, or with `python3` when `jq` is not installed, reading the credentials from the environment, and pipes the resulting `Secret` into `kubectl apply -f -`. The password is never a command-line argument and the manifest never touches the disk. `apply` creates or updates, so the operation is idempotent.

The credentials used by the kubeconfig must be allowed to create and update secrets in the target namespace.

## RBAC

The action applies whatever manifests you give it, waits for rollouts, and optionally manages a pull secret, so a namespace-scoped `Role` has to cover the kinds you actually deploy. This is a working starting point for a namespace with deployments, services, configmaps, secrets, and ingresses, used with `create_namespace: "false"`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: github-deployer
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets", "serviceaccounts", "persistentvolumeclaims"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["ingresses", "networkpolicies"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["autoscaling"]
    resources: ["horizontalpodautoscalers"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

`kubectl rollout status` reads `deployments`, `statefulsets`, or `daemonsets` and their pods, which the rules above already allow.

With `create_namespace: "true"` (the default) the same credentials also need cluster-scoped rights, because namespaces are not namespaced objects:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: github-deployer-namespaces
rules:
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "create", "patch", "update"]
```

Prefer `create_namespace: "false"` and a namespace created once by an administrator: the deploy credentials then stay namespace-scoped.

With `prune: "true"`, the credentials must also be allowed to `delete` every kind that carries the prune label, and `prune_label` has to select only the resources this deploy owns.

## Requirements

Linux runners, self-hosted or GitHub-hosted. See "Runner requirements" above for the exact tool list.

Store your kubeconfig in GitHub Secrets, for example:

```text
KUBECONFIG_B64
```

The kubeconfig can be provided as raw YAML or base64-encoded YAML.

## Security

Do not commit kubeconfig files, registry credentials, or generated Kubernetes secrets to your repository.

Use a Kubernetes ServiceAccount with the minimum permissions required for the target namespace, and prefer `create_namespace: "false"` so those permissions can stay namespace-scoped.

For private registries, prefer a pull-only robot account or token for the Kubernetes image pulls.

For Harbor or OVHcloud Managed Private Registry, create separate robot accounts for:

```text
- CI/CD push access
- Kubernetes pull-only access
```

Read "Shared self-hosted runners" above for what the action does to protect these secrets on a shared machine, and for the residual risk it cannot remove.

## Development

`action.yml` is checked on every push and pull request by `.github/workflows/ci.yml`:

- `action.yml`, the example workflow, and the workflows themselves must parse as YAML
- `scripts/lint-steps.py` extracts the `run` body of every composite step, replaces the `${{ ... }}` expressions with a placeholder, and runs `shellcheck` on each one

Run the same check locally with:

```bash
python3 -m pip install pyyaml
python3 scripts/lint-steps.py action.yml
```

Releases are tagged `vX.Y.Z`. `.github/workflows/release.yml` then moves the `vX` and `vX.Y` alias tags to that commit, so `v1` always points at the latest release.

How each step works, the constraints behind the implementation, and how to exercise a step locally are documented in [`docs/`](docs/README.md).

## License

MIT
