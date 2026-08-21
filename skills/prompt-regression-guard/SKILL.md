---
name: prompt-regression-guard
description: Runs your prompt templates against a versioned snapshot suite before every deploy, diffing model outputs field-by-field to flag silent behavior drift.
argument-hint: [prompt-dir]
---

# Prompt Regression Guard

Catches silent prompt breakage before it reaches production, not after.

## Input

$ARGUMENTS

## How It Works

1. Load prompt templates and their last-known-good output snapshots.
2. Re-run each template against the current model and config.
3. Diff structured output fields rather than raw text to ignore harmless wording changes.
4. Score each diff's severity using configurable per-field weights.
5. Emit a pass or fail report and update snapshots once changes are approved.