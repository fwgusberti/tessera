# Kubernetes Manifests

Kubernetes manifests are deferred until the production provider is selected (Complexity Tracking deviation in plan.md).

The Compose-based dev environment (`deploy/docker-compose.yml`) is fully functional for local development and integration testing.

When the provider is chosen, add manifests here for:
- `api-deployment.yaml`
- `worker-deployment.yaml`
- `mcp-deployment.yaml`
- `web-deployment.yaml`
- `postgres-service.yaml` (or managed DB reference)
- `redis-service.yaml` (or managed cache reference)
- `ingress.yaml`
- `secrets.yaml` (external-secrets or SOPS-encrypted)
