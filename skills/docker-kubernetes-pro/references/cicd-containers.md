# CI/CD for Containers

## Build & Push Pipeline

Build the image once per commit, tag it with the commit SHA (not just `latest`), push it to the registry, then deploy that exact tag — this makes every deployed version traceable back to the exact source commit that produced it.

## Rollout Strategies

- **Rolling update** (`maxUnavailable: 0`, `maxSurge: 1`): default choice for most services; zero downtime, gradual replacement.
- **Blue-green**: run the new version fully alongside the old, then switch traffic at once — useful when a rolling update's mixed-version window is itself risky (e.g. an incompatible schema change).
- **Canary**: route a small percentage of traffic to the new version first, then ramp up — useful for catching a regression before it affects all users.

## Automated Rollback

Wire a deploy's success criteria to actual health signals (error rate, latency) post-rollout, and automate rollback to the previous known-good image tag on failure, rather than relying on someone noticing a dashboard.

## Environment Parity

Build the same image for staging and production and promote it forward rather than rebuilding per environment — rebuilding risks a subtly different image (different dependency resolution, different base image patch level) reaching production than the one actually tested in staging.
