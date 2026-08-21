# Health & Resource Management

## Readiness vs. Liveness Probes

A **readiness** probe controls whether a pod receives traffic — a pod that's up but not yet ready (still loading a cache, waiting on a DB connection) should fail readiness so it's removed from the Service's endpoints, not restarted. A **liveness** probe controls whether Kubernetes restarts the container — reserve it for detecting a genuinely stuck/deadlocked process, since a liveness probe that's too aggressive causes restart loops under normal load spikes.

## Resource Requests & Limits

`requests` is what the scheduler guarantees the pod when placing it; `limits` is the hard ceiling. Set both — no requests means the scheduler can over-pack a node, and no limits means one runaway pod can starve its neighbors of CPU/memory.

## Horizontal Pod Autoscaling (HPA)

Scale on a metric that actually reflects load (CPU, custom request-latency/queue-depth metrics) rather than always fixing replica count manually. Set sensible min/max bounds so a metric spike can't scale to an unbounded (and expensive) replica count.

## Startup Time

If a service has a slow cold start (JVM warm-up, large in-memory cache load), use a `startupProbe` with a longer allowance before liveness checks begin, instead of setting liveness's `initialDelaySeconds` so high it delays detecting a genuinely stuck pod later on.
