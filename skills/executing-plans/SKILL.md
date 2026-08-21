---
name: executing-plans
description: Tracks execution of a previously written multi-step development plan by checkpointing progress after each step and resuming cleanly if the session is interrupted.
argument-hint: [plan-file]
---

# Executing Plans

Turns a written plan into a resumable, trackable execution instead of a document that goes stale mid-run.

## Input

$ARGUMENTS

## How It Works

1. Load the plan and confirm each step's scope, order, and completion criteria.
2. Execute the next incomplete step and validate it against its stated criteria.
3. Record the step as complete in a checkpoint file before moving to the next one.
4. On resume after an interruption, read the checkpoint file to find the last completed step.
5. Continue execution from that point without repeating or skipping any step.