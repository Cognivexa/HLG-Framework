---
name: stale-branch-cleanup-planner
description: Scans all local and remote branches to find ones already merged, abandoned for 60+ days, or orphaned from deleted PRs, then produces a safe-to-delete list with the evidence behind each entry. It never deletes anything itself; it only outputs the plan and the exact git commands to run.
argument-hint: [days-inactive-threshold]
---

# Stale Branch Cleanup Planner

Tells you exactly which branches are safe to delete, and why, without touching a single one.

## Input

$ARGUMENTS

## How It Works

1. List all local and remote branches with their last-commit timestamps
2. Check each branch's merge status against the main branch
3. Cross-reference branches against closed or deleted PRs
4. Flag branches inactive beyond the threshold as cleanup candidates
5. Output a plan with reasoning and the exact git commands to delete each