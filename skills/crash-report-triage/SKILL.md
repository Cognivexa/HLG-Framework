---
name: crash-report-triage
description: Parses symbolicated iOS/Android crash logs from Crashlytics or Sentry exports and clusters them by root stack frame, ranking each cluster by device, OS version, and affected-user impact. Drafts a short triage note per cluster with the suspected file/line and repro hints.
argument-hint: [crash-log-export-path]
---

# Mobile Crash Report Triage

Turns a flood of crash logs into a ranked, actionable fix list.

## Input

$ARGUMENTS

## How It Works

1. Ingest the symbolicated crash log export and parse stack traces
2. Cluster crashes by matching root exception frame and thread
3. Score each cluster by affected user count, OS version, and device model
4. Rank clusters from highest to lowest impact
5. Draft a triage note per cluster with suspected file/line and repro hints