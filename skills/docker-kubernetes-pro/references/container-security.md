# Container Security

## Non-Root by Default

```dockerfile
RUN addgroup -S app && adduser -S app -G app
USER app
```

Running as root inside the container means a container-escape vulnerability hands the attacker root on the host. Create and switch to an unprivileged user in the Dockerfile, and reinforce it with `runAsNonRoot: true` in the pod's `securityContext` so Kubernetes refuses to run the pod otherwise.

## Image Scanning

Scan every image for known-vulnerable packages (Trivy, Grype, or a registry's built-in scanner) as part of the CI pipeline, and block the deploy on critical/high findings rather than only reviewing scan results after the fact.

## Read-Only Root Filesystem

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

Mount an explicit `emptyDir` volume for any directory the app genuinely needs to write to (a cache dir, `/tmp`) rather than leaving the whole filesystem writable by default.

## Secrets Never in the Image

A secret baked into an image layer is recoverable by anyone who can pull the image, even if a later layer "removes" the file — layers are immutable and cumulative. Always inject secrets at runtime via environment variables or mounted Secret volumes.
