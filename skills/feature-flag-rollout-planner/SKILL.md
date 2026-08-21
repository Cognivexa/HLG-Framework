---
name: feature-flag-rollout-planner
description: Plan a staged feature flag rollout with explicit rollback criteria and monitoring checkpoints per stage.
argument-hint: [feature-name]
---

# Feature Flag Rollout Planner

Plan the rollback criteria before the rollout starts, not after something breaks.

## Input

$ARGUMENTS

## How It Works

1. Define rollout stages by percentage or cohort
2. Set explicit success and rollback criteria for each stage
3. Identify the metrics to monitor at each checkpoint
4. Define the kill-switch process and who can pull it
5. Document the full rollout plan for on-call visibility