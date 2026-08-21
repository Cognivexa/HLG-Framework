---
name: writing-plans
description: Invoked before implementation work begins on any multi-step coding task, this skill converts a spec or requirement into an ordered, checkable plan with explicit in-scope and out-of-scope boundaries. It forces scope discipline up front so execution does not drift once code changes start.
argument-hint: [spec-or-requirement]
---

# Writing Plans

Turns a vague requirement into a checklist with edges, instead of a pile of code that drifts as it goes.

## Input

$ARGUMENTS

## How It Works

1. Read the spec or requirement in full before writing a single line of code.
2. Identify the discrete milestones needed to satisfy the requirement and order them by dependency.
3. Draft explicit in-scope and out-of-scope statements so later work cannot silently expand.
4. Convert each milestone into a checkable task with a clear definition of done.
5. Surface open questions or ambiguous requirements as blocking items before implementation starts.