---
name: secrets-in-code-scanner
description: Sweeps repository history and working tree for hardcoded API keys, tokens, and credentials using entropy analysis and provider-specific pattern matching, then generates revocation steps.
argument-hint: [repo-path]
---

# Secrets In Code Scanner

Finds the API key your teammate committed three months ago before an attacker does.

## Input

$ARGUMENTS

## How It Works

1. Walk the full git history and current working tree file by file
2. Run entropy analysis alongside provider-specific regex signatures for known key formats
3. Filter out placeholder and test-fixture values to cut false positives
4. Trace each confirmed secret to its commit, author, and first-exposed date
5. Output a revocation checklist with provider-specific rotation links per finding