---
name: regression-triage
description: Triage a reported regression: bisect the likely commit range, reproduce locally, and hand off with a minimal repro.
argument-hint: [bug-report]
---

# Regression Triage

Hand off a minimal, reproducible case instead of a vague bug report.

## Input

$ARGUMENTS

## How It Works

1. Reproduce the reported behavior locally before investigating further
2. Bisect the likely commit range using known-good and known-bad points
3. Narrow the repro to the smallest input that still triggers it
4. Identify the responsible change and its intended purpose
5. Hand off with the minimal repro and a suggested owner