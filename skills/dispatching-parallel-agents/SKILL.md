---
name: dispatching-parallel-agents
description: Splits a batch of independent tasks with no shared dependencies across multiple subagents dispatched at once, then reconciles their results into a single output.
argument-hint: [task-list]
---

# Dispatching Parallel Agents

Turns a pile of unrelated tasks into simultaneous subagent runs instead of a slow sequential queue.

## Input

$ARGUMENTS

## How It Works

1. Confirm each task in the batch has no shared files or state with the others.
2. Assign one subagent per independent task with a self-contained prompt.
3. Dispatch all subagents concurrently rather than one after another.
4. Collect each subagent's output as it completes.
5. Merge the results, checking for conflicts or duplicated work before finalizing.