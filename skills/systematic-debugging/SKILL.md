---
name: systematic-debugging
description: Applies a disciplined debugging process to any bug, failing test, or unexpected behavior before a fix is proposed. It reproduces the issue reliably, narrows the root cause through bisection-style isolation, and confirms the fix resolves the actual cause rather than a symptom.
argument-hint: [bug-or-failure]
---

# Systematic Debugging

Replaces guess-and-patch fixes with a narrowed-down, verified root cause.

## Input

$ARGUMENTS

## How It Works

1. Reproduce the failure with a minimal, repeatable case before touching any code.
2. Bisect the surrounding code, inputs, or recent commits to narrow down where the behavior diverges.
3. Form a specific hypothesis about the root cause and test it in isolation.
4. Implement the smallest fix that addresses the confirmed root cause, not just the visible symptom.
5. Re-run the original reproduction plus related tests to verify the failure is gone and nothing else broke.