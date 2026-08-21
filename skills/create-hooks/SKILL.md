---
name: create-hooks
description: Provides expert guidance for authoring Claude Code hooks, covering event selection, matcher configuration, and writing hook scripts that run fast and fail safely.
argument-hint: [hook-event]
---

# Create Hooks

Turns from now on always do X requests into a properly wired hook instead of an instruction that quietly gets forgotten.

## Input

$ARGUMENTS

## How It Works

1. Identify which lifecycle event, such as PreToolUse or PostToolUse, actually corresponds to the desired trigger point.
2. Write a matcher that targets the right tools or commands without over- or under-matching.
3. Draft the hook script logic, keeping it short-running and side-effect-aware so it cannot stall the session.
4. Add safe failure handling so a hook error blocks or warns as intended rather than crashing silently.
5. Wire the hook into settings.json and describe how to verify it fires correctly on a test action.