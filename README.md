# Kubernetes Deploy by RelyBytes

Deploy services to a Kubernetes cluster by applying YAML manifests with namespace management, recursive manifest discovery, placeholder replacements, optional private registry pull secret creation, image updates, dry-run support, pruning, and rollout management.

## Features

- Configure Kubernetes access from raw or base64-encoded kubeconfig
- Select kubeconfig context
- Create namespace if missing
- Support namespace-scoped ServiceAccounts
- Apply YAML/JSON manifests from files or directories
- Recursively discover manifests in subdirectories
- Support Kustomize with `kubectl apply -k`
- Replace placeholders before deploy
- Run `envsubst` on manifests
- Optionally create or update an `imagePullSecret` for private registries
- Update container images with `kubectl set image`
- Support client/server dry-run
- Optional `kubectl --prune`
- Wait for deployment, statefulset, and daemonset rollouts
- Output applied resources, rollout status, and deployment timestamp

## Usage

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

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

## Usage with a private registry

Use this when your Kubernetes cluster needs to pull images from a private registry such as GHCR, Harbor, Docker Hub private repositories, or OVHcloud Managed Private Registry.

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

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

```yaml
- name: Deploy with Kustomize
  uses: relybytes/actions-kubernetes-deploy@v1
  with:
    kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
    namespace: production
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
    manifests: ./k8s
    set_image: |
      deployment/api=app=ghcr.io/myorg/api:${{ github.sha }}
      deployment/worker=worker=ghcr.io/myorg/worker:${{ github.sha }}
```

## Inputs

| Input                    | Required | Default                | Description                                                                                                             |
| ------------------------ | -------: | ---------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `kubeconfig`             |      yes |                        | Kubeconfig content, raw YAML or base64-encoded                                                                          |
| `context`                |       no | `""`                   | Kubeconfig context to use                                                                                               |
| `namespace`              |      yes |                        | Target Kubernetes namespace                                                                                             |
| `create_namespace`       |       no | `true`                 | Create namespace if it does not exist                                                                                   |
| `manifests`              |      yes |                        | Manifest file, directory, or multiple paths. Directories are scanned recursively for `.yaml`, `.yml`, and `.json` files |
| `kustomize`              |       no | `false`                | Apply manifests using `kubectl apply -k`                                                                                |
| `replacements`           |       no | `""`                   | Newline-separated `KEY=VALUE` placeholder replacements                                                                  |
| `set_image`              |       no | `""`                   | Newline-separated `resource=container=image` entries                                                                    |
| `env_substitution`       |       no | `false`                | Apply `envsubst` to manifests                                                                                           |
| `validate`               |       no | `true`                 | Run `kubectl apply` with validation                                                                                     |
| `dry_run`                |       no | `none`                 | Dry-run mode: `none`, `client`, or `server`                                                                             |
| `prune`                  |       no | `false`                | Enable `kubectl --prune`                                                                                                |
| `prune_label`            |       no | `""`                   | Label selector required when prune is enabled                                                                           |
| `wait`                   |       no | `true`                 | Wait for rollout after apply                                                                                            |
| `wait_resources`         |       no | `""`                   | Resources to wait on                                                                                                    |
| `wait_timeout`           |       no | `300s`                 | Rollout wait timeout                                                                                                    |
| `kubectl_version`        |       no | `""`                   | kubectl version to install, for example `v1.30.0`                                                                       |
| `create_registry_secret` |       no | `false`                | Create or update a Kubernetes `imagePullSecret` for private registries                                                  |
| `registry_server`        |       no | `""`                   | Container registry server, for example `ghcr.io`, `registry.example.com`, or an Harbor/OVH registry URL                 |
| `registry_username`      |       no | `""`                   | Container registry username                                                                                             |
| `registry_password`      |       no | `""`                   | Container registry password or token                                                                                    |
| `registry_email`         |       no | `devops@relybytes.com` | Container registry email                                                                                                |
| `registry_secret_name`   |       no | `""`                   | Kubernetes `imagePullSecret` name to create or update                                                                   |

## Outputs

| Output              | Description                                       |
| ------------------- | ------------------------------------------------- |
| `applied_resources` | Resources applied to the cluster                  |
| `rollout_status`    | Rollout status: `success`, `failed`, or `skipped` |
| `deployment_time`   | UTC deployment timestamp                          |

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

## Private registry pull secrets

When `create_registry_secret` is set to `"true"`, the action creates or updates a Kubernetes Docker registry secret using:

```bash
kubectl create secret docker-registry ... --dry-run=client -o yaml | kubectl apply -f -
```

This makes the operation idempotent.

The ServiceAccount used by the kubeconfig must have permission to create or update secrets in the target namespace.

Example RBAC permission:

```yaml
rules:
  - apiGroups: [""]
    resources:
      - secrets
    verbs:
      - get
      - list
      - watch
      - create
      - update
      - patch
      - delete
```

## Requirements

This action is designed for Linux runners such as `ubuntu-latest`.

Store your kubeconfig in GitHub Secrets, for example:

```text
KUBECONFIG_B64
```

The kubeconfig can be provided as raw YAML or base64-encoded YAML.

## Security

Do not commit kubeconfig files, registry credentials, or generated Kubernetes secrets to your repository.

Use a Kubernetes ServiceAccount with the minimum permissions required for the target namespace.

For private registries, prefer a pull-only robot account or token for Kubernetes image pulls.

For Harbor or OVHcloud Managed Private Registry, create separate robot accounts for:

```text
- CI/CD push access
- Kubernetes pull-only access
```

## License

MIT
