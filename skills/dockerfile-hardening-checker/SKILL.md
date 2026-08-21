---
name: dockerfile-hardening-checker
description: Scans Dockerfiles and Compose files for insecure base images, root-user execution, exposed secrets, and missing multi-stage build patterns, then rewrites offending lines with hardened equivalents.
argument-hint: [dockerfile-path]
---

# Dockerfile Hardening Checker

Turns a sloppy Dockerfile into a production-hardened one in seconds, not a code review cycle.

## Input

$ARGUMENTS

## How It Works

1. Parse the target Dockerfile and any referenced Compose files into an instruction tree
2. Flag root-user execution, latest-tag base images, and world-writable file permissions
3. Cross-reference base image tags against a curated list of minimal and distroless alternatives
4. Rewrite flagged instructions in place, adding USER, HEALTHCHECK, and multi-stage build steps
5. Emit a before/after diff summary with a hardening score