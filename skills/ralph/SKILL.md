---
name: ralph
description: Runs the same fixed prompt repeatedly against a task backlog until it is empty, relying on statelessness and idempotent checks rather than long-running memory between iterations. Named after the well-known autonomous-loop coding technique.
argument-hint: [task-backlog]
---

# Ralph

Clears a backlog one dumb, repeatable pass at a time instead of one clever, stateful marathon.

## Input

$ARGUMENTS

## How It Works

1. Read the current backlog and pick the next unfinished item using only what is on disk, not memory of prior runs.
2. Check whether that item is already done by inspecting real state, avoiding duplicate work.
3. Execute the fixed prompt against that single item and make the smallest change that completes it.
4. Update the backlog file to mark the item resolved before moving to the next one.
5. Repeat the same fixed loop until the backlog file reports no remaining items.