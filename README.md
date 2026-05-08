# Kubernetes Deploy by RelyBytes

Deploy services to a Kubernetes cluster by applying YAML manifests with namespace creation, placeholder replacements, image updates, dry-run support, pruning, and rollout management.

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
          kubeconfig: ${{ secrets.KUBECONFIG }}
          namespace: production
          manifests: ./k8s
          replacements: |
            __IMAGE__=ghcr.io/myorg/api:${{ github.sha }}
            __APP_ENV__=production
          wait: "true"
          wait_timeout: "300s"
```

## Inputs

| Input              | Required | Default | Description                                            |
| ------------------ | -------: | ------- | ------------------------------------------------------ |
| `kubeconfig`       |      yes |         | Kubeconfig content, raw YAML or base64-encoded         |
| `context`          |       no | `""`    | Kubeconfig context to use                              |
| `namespace`        |      yes |         | Target Kubernetes namespace                            |
| `create_namespace` |       no | `true`  | Create namespace if it does not exist                  |
| `manifests`        |      yes |         | Manifest file, directory, or multiple paths            |
| `kustomize`        |       no | `false` | Apply manifests using `kubectl apply -k`               |
| `replacements`     |       no | `""`    | Newline-separated `KEY=VALUE` placeholder replacements |
| `set_image`        |       no | `""`    | Newline-separated `resource=container=image` entries   |
| `env_substitution` |       no | `false` | Apply `envsubst` to manifests                          |
| `validate`         |       no | `true`  | Run `kubectl apply` with validation                    |
| `dry_run`          |       no | `none`  | Dry-run mode: `none`, `client`, or `server`            |
| `prune`            |       no | `false` | Enable `kubectl --prune`                               |
| `prune_label`      |       no | `""`    | Label selector required when prune is enabled          |
| `wait`             |       no | `true`  | Wait for rollout after apply                           |
| `wait_resources`   |       no | `""`    | Resources to wait on                                   |
| `wait_timeout`     |       no | `300s`  | Rollout wait timeout                                   |
| `kubectl_version`  |       no | `""`    | kubectl version to install, for example `v1.30.0`      |

## Outputs

| Output              | Description                                       |
| ------------------- | ------------------------------------------------- |
| `applied_resources` | Resources applied to the cluster                  |
| `rollout_status`    | Rollout status: `success`, `failed`, or `skipped` |
| `deployment_time`   | UTC deployment timestamp                          |

## Requirements

This action is designed for Linux runners such as `ubuntu-latest`.

Store your kubeconfig in GitHub Secrets, for example:

```text
KUBECONFIG
```

## Security

Do not commit kubeconfig files to your repository.

Use a Kubernetes service account with the minimum permissions required for the target namespace.

## License

MIT
