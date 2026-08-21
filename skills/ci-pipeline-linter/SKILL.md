---
name: ci-pipeline-linter
description: Lints GitHub Actions, GitLab CI, and CircleCI YAML configs for slow, flaky, or insecure pipeline patterns such as unpinned actions, missing caching, and unbounded job timeouts.
argument-hint: [workflow-file-or-dir]
---

# CI Pipeline Linter

Catches the pipeline mistakes that quietly cost you build minutes and security posture before they ship.

## Input

$ARGUMENTS

## How It Works

1. Detect the CI provider from file structure and parse each workflow into a job graph
2. Check every third-party action or job reference against pinned-SHA and version-range rules
3. Flag missing timeout-minutes, concurrency groups, and dependency-caching steps
4. Simulate the job graph to surface redundant or serially-blocking steps that could run in parallel
5. Output a prioritized fix list with inline YAML patches ready to apply