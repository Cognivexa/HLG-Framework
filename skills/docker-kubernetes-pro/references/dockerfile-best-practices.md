# Dockerfile Best Practices

## Multi-Stage Builds

Separate the stage that compiles/builds the app from the stage that runs it, and copy only the build output into the final image:

```dockerfile
FROM node:20-alpine AS build
...
RUN npm run build

FROM node:20-alpine
COPY --from=build /app/dist ./dist
```

This keeps compilers, dev dependencies, and source maps out of the shipped image, cutting both size and attack surface.

## Layer Caching

Order instructions from least to most frequently changing: copy dependency manifests (`package.json`/`requirements.txt`) and install dependencies before copying the rest of the source. That way, a source-only change doesn't invalidate the (usually slow) dependency-install layer.

## Minimal Base Images

Prefer `-alpine` or `-slim` variants, or a distroless image, over the full default base — fewer packages means a smaller attack surface and fewer things needing patches. Weigh this against alpine's musl libc occasionally causing subtle compatibility issues with native dependencies.

## .dockerignore

Add a `.dockerignore` excluding `.git`, `node_modules`, and local env files — without it, the entire build context (including secrets accidentally left in a local `.env`) is sent to the Docker daemon and can end up copied into a layer.
