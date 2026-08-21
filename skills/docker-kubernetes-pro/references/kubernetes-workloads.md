# Kubernetes Workloads

## Deployments vs. StatefulSets

Use a `Deployment` for stateless, interchangeable replicas (a typical API server). Use a `StatefulSet` only when pods need a stable identity and ordered, persistent storage (a database, a message broker) — reaching for a Deployment for a genuinely stateful workload is a common source of data-consistency bugs.

## Services

A `ClusterIP` Service gives stable internal DNS to a set of pods selected by label; a pod's IP changes on every restart, so nothing should hardcode a pod IP. Use `LoadBalancer` or an `Ingress` for external traffic rather than exposing a `NodePort` directly in production.

## ConfigMaps & Secrets

Put non-sensitive configuration in a `ConfigMap` and sensitive values in a `Secret` — both can be mounted as environment variables or files, but only `Secret` values are (base64-encoded, and with RBAC/encryption-at-rest configured) treated as sensitive by the cluster's tooling.

## Labels & Selectors

Keep label selectors on Services and Deployments precise and consistent (`app: api`, `tier: backend`) — an overly broad selector can cause a Service to route traffic to pods from an unrelated Deployment that happens to share a label.
