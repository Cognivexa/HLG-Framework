---
name: using-superpowers
description: Acts as the entry point for coding, testing, or refactoring work by surveying which workflow skills apply to the task and sequencing them before any implementation begins.
argument-hint: [task-description]
---

# Using Superpowers

Turns a loose task request into an ordered plan of the right skills instead of an immediate dive into code.

## Input

$ARGUMENTS

## How It Works

1. Read the incoming task and classify its type, such as bug fix, new feature, refactor, or review.
2. Check the list of available workflow skills against the task classification.
3. Select the applicable skills and determine the order they should run in.
4. Announce the sequence before invoking the first skill.
5. Hand off to each skill in turn, confirming completion before advancing to the next.