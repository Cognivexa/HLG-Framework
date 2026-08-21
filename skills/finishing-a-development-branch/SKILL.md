---
name: finishing-a-development-branch
description: Runs a completion checklist covering lint, build, tests, documentation, and leftover TODOs before a development branch is considered ready to merge.
argument-hint: [branch-name]
---

# Finishing A Development Branch

Turns "I think it's done" into a checked-off list before the branch is declared mergeable.

## Input

$ARGUMENTS

## How It Works

1. Run the linter and build across the full branch diff and confirm both are clean.
2. Run the complete test suite and record the pass results.
3. Scan the changed files for leftover TODO, FIXME, or debug statements.
4. Confirm documentation and changelog entries reflect the new behavior.
5. Summarize the checklist results and flag any item that still needs attention before merge.