---
name: flaky-test-hunter
description: Identify flaky tests from CI history, isolate the non-determinism, and propose a fix instead of a blanket retry.
argument-hint: [ci-log-or-test-path]
---

# Flaky Test Hunter

Find the actual source of non-determinism instead of papering over it with retries.

## Input

$ARGUMENTS

## How It Works

1. Scan CI history for tests with inconsistent pass/fail patterns
2. Reproduce the failure locally with repeated or randomized runs
3. Isolate the non-determinism: timing, ordering, shared state, or environment
4. Propose a fix that removes the root cause, not a retry wrapper
5. Verify the fix with a stress-test run before closing it out