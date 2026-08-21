---
name: audit-evidence-collector
description: Organize evidence artifacts against a control list so audit prep isn't a last-minute scramble.
argument-hint: [control-list]
---

# Audit Evidence Collector

Know exactly which controls are missing evidence before the auditor asks.

## Input

$ARGUMENTS

## How It Works

1. Load the control list for the relevant framework
2. Match existing artifacts to each control
3. Flag controls with no evidence or stale evidence
4. Organize matched evidence by control for easy auditor review
5. Report the remaining gap list with a suggested collection owner