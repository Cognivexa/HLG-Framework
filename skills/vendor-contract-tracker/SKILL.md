---
name: vendor-contract-tracker
description: Extract renewal dates, notice periods, and auto-renewal terms from contract text into a tracked summary.
argument-hint: [contract-file]
---

# Vendor Contract Tracker

Never let an auto-renewal clause be a surprise again.

## Input

$ARGUMENTS

## How It Works

1. Read the full contract text, not just the summary page
2. Extract renewal date, notice period, and auto-renewal terms
3. Flag ambiguous or unusually short notice periods
4. Calculate the actual cancellation deadline from the notice period
5. Summarize key terms in a consistent, comparable format