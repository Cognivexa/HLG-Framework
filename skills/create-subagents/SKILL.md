---
name: create-subagents
description: Provides expert guidance for designing Claude Code subagents, covering tool-access scoping, system-prompt writing, and deciding when a task should be delegated rather than handled inline.
argument-hint: [subagent-purpose]
---

# Create Subagents

Turns an all-purpose helper agent into a narrowly scoped specialist instead of one that reaches for tools it does not need.

## Input

$ARGUMENTS

## How It Works

1. Clarify the task category the subagent should own and confirm it benefits from running in a separate context.
2. Select the minimal tool set the subagent needs and exclude anything that expands its blast radius unnecessarily.
3. Write a system prompt that states the subagent's role, boundaries, and expected report format.
4. Define criteria for when the parent should delegate to this subagent versus completing the work inline.
5. Test the subagent on a representative task and check whether its final report gives the parent enough to act on.