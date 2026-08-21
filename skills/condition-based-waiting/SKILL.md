---
name: condition-based-waiting
description: Replaces fixed sleep or delay calls with polling against a real readiness condition, such as a process starting, a file appearing, or an endpoint responding. This avoids both premature failures and wasted idle time.
argument-hint: [readiness-check]
---

# Condition-Based Waiting

Waits for the thing to actually be ready instead of guessing how long that takes.

## Input

$ARGUMENTS

## How It Works

1. Identify the concrete signal that proves readiness, such as a port opening or a status file being written.
2. Replace any fixed-duration sleep call with a polling loop that checks that exact signal.
3. Set a short poll interval and a sane maximum timeout to avoid hanging indefinitely.
4. Fail fast with a clear error message once the timeout is reached without the condition being met.
5. Log how long the wait actually took so future runs can be tuned if needed.