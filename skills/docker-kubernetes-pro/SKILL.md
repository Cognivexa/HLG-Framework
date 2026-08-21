---
name: docker-kubernetes-pro
description: Expert in containerizing and deploying applications: minimal multi-stage Docker images and secure, resource-aware Kubernetes manifests.
when_to_use: Use when writing or reviewing a Dockerfile, docker-compose setup, or Kubernetes manifests, sizing resource requests/limits, configuring health checks, hardening container security, or setting up a CI/CD pipeline for containers.
metadata:
  domain: Containers & Orchestration
  platform: DevOps
  role: expert
  scope: implementation
  output: config
  relatedSkills: Fullstack Guardian, Security Reviewer, Python Pro, TypeScript Pro
---

# Docker & Kubernetes Pro

Expert in containerizing and deploying applications: minimal multi-stage Docker images and secure, resource-aware Kubernetes manifests.

## Core Workflow

1. **Analyze requirements** — Understand the app's runtime, existing deployment target, and current Dockerfile/manifests if any.
2. **Design the image** — Plan a multi-stage build that separates build-time and run-time dependencies.
3. **Implement** — Write the Dockerfile/manifests using minimal base images and least-privilege defaults.
4. **Validate** — Build locally, scan the image for vulnerabilities, and lint manifests (hadolint, kubeval/kubeconform).
5. **Optimize** — Minimize image layers/size, tune resource requests/limits, and configure health checks.
6. **Test & secure** — Verify the container runs as non-root, secrets aren't baked into the image, and rollouts are safe.

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|---|---|---|
| Dockerfile Best Practices | references/dockerfile-best-practices.md | Multi-stage builds, layer caching, minimal images |
| Kubernetes Workloads | references/kubernetes-workloads.md | Deployments, Services, ConfigMaps/Secrets |
| Health & Resource Management | references/health-resource-management.md | Probes, requests/limits, HPA |
| Container Security | references/container-security.md | Non-root users, image scanning, secrets handling |
| CI/CD for Containers | references/cicd-containers.md | Build/push pipelines, rollout strategies |

## Key Implementation Patterns

### Multi-Stage Dockerfile
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
USER app
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

### Kubernetes Deployment with Probes and Limits
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          image: registry.example.com/api:1.4.0
          resources:
            requests: { cpu: "100m", memory: "128Mi" }
            limits: { cpu: "500m", memory: "256Mi" }
          readinessProbe:
            httpGet: { path: /healthz, port: 3000 }
            initialDelaySeconds: 5
          livenessProbe:
            httpGet: { path: /healthz, port: 3000 }
            initialDelaySeconds: 15
```

### Secrets via Environment, Not Baked In
```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: database-url
```

### Non-Root User Enforcement
```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

### Zero-Downtime Rolling Update
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0
    maxSurge: 1
```

## Constraints

**MUST DO**
- Use multi-stage builds to keep build-time dependencies out of the final image
- Pin base image versions (node:20-alpine, not node:latest)
- Run containers as a non-root user
- Set resource requests and limits on every workload
- Configure readiness and liveness probes for every service
- Load secrets from a secrets manager or Kubernetes Secret, never bake them into the image
- Scan images for known vulnerabilities before deploying
- Use maxUnavailable: 0 for zero-downtime rolling updates on user-facing services
- Keep images small using slim/alpine/distroless bases and minimizing layers
- Set explicit health-check timeouts that match the app's real startup time

**MUST NOT DO**
- Use the latest tag for any image in a production manifest
- Run a container as root without a documented reason
- Bake API keys or credentials into a Docker image layer
- Skip resource limits, letting one pod starve others on the same node
- Expose the Docker daemon socket to a container without a strong reason
- Ignore image scan results for high/critical vulnerabilities
- Use hostNetwork or hostPID unless there is a specific, justified need
- Deploy without a readiness probe, causing traffic to hit a not-yet-ready pod

## Output Templates

When implementing, provide:

1. Dockerfile and/or Kubernetes manifests
2. Resource/probe configuration
3. Security context settings
4. Scan/lint results
5. Brief explanation of the deployment strategy chosen

## Knowledge Reference

Docker multi-stage builds, OCI image spec, Kubernetes Deployments/Services/Ingress, Helm, kubeval/kubeconform, hadolint, Trivy/Grype scanning, HPA, resource requests/limits, rolling/blue-green/canary deploys