---
name: verification-before-completion
description: Blocks premature claims of a task being done, fixed, or passing by requiring the relevant tests, build, or lint to actually be run and their output cited as evidence.
argument-hint: [completed-task]
---

# Verification Before Completion

Replaces confident assertions of success with actual command output as proof.

## Input

$ARGUMENTS

## How It Works

1. Identify which commands, such as the test suite, build, or linter, are relevant to the change made.
2. Run each identified command and capture its full output.
3. Compare the output against the expected passing state, not against memory of prior runs.
4. Flag any failures, warnings, or skipped tests instead of glossing over them.
5. Only report the task as complete once the cited evidence supports that claim.