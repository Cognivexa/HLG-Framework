---
name: create-plans
description: Builds a hierarchical project plan of epics, tasks, and subtasks structured so a single agent can execute it sequentially without losing track of prior context.
argument-hint: [project-description]
---

# Create Plans

Turns a one-line feature request into an ordered, checkable task tree instead of a wall of text an agent re-reads from scratch every step.

## Input

$ARGUMENTS

## How It Works

1. Clarify the overall goal and constraints, then split the work into a small number of epics.
2. Break each epic into concrete tasks that can be completed and verified independently.
3. Decompose any task that touches multiple files or systems into ordered subtasks.
4. Sequence the tree so each step's output supplies exactly the context the next step needs.
5. Attach a completion check to each task so progress can be verified before moving on.