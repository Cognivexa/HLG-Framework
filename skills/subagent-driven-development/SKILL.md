---
name: subagent-driven-development
description: Coordinates implementation of a multi-task plan by identifying which tasks are independent enough to run in parallel subagents and which require sequential handoffs.
argument-hint: [plan-file-or-tasks]
---

# Subagent-Driven Development

Turns a flat task list into a coordinated dispatch of parallel and sequential work instead of one long serial chain.

## Input

$ARGUMENTS

## How It Works

1. Parse the plan into discrete tasks and map their inputs, outputs, and shared files.
2. Build a dependency graph identifying which tasks have no overlapping resources.
3. Dispatch independent tasks to separate subagents to run concurrently.
4. Queue dependent tasks behind the subagent output they rely on.
5. Reconcile all subagent results into a single coherent implementation and check for conflicts.