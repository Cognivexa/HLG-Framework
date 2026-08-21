---
name: debug-like-an-expert
description: Guides systematic root-cause investigation for difficult bugs by requiring full context gathering, multiple competing hypotheses, and isolated testing of each one before any fix is attempted.
argument-hint: [bug-description]
---

# Debug Like An Expert

Turns guess-and-check debugging into a disciplined investigation instead of a lucky patch.

## Input

$ARGUMENTS

## How It Works

1. Collect the full error output, stack trace, logs, and recent changes surrounding the failure.
2. Reproduce the bug reliably before touching any code.
3. Draft at least three distinct hypotheses for the root cause, ranked by plausibility.
4. Design a minimal test or probe for the top hypothesis and run it in isolation.
5. Discard disproven hypotheses, refine the fix, and confirm the corrected behavior against the original reproduction case.