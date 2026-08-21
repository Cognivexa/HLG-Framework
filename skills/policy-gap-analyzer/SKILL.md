---
name: policy-gap-analyzer
description: Compare an internal policy document against a named framework or checklist and report specific gaps.
argument-hint: [policy-doc] [framework-name]
---

# Policy Gap Analyzer

Report specific, cited gaps instead of a vague "mostly compliant" verdict.

## Input

$ARGUMENTS

## How It Works

1. Load the policy document and the named framework or checklist
2. Match each framework requirement to a specific policy clause
3. Flag requirements with no matching clause as a gap
4. Flag clauses that partially address a requirement, not just missing ones
5. Report gaps with the specific requirement cited, ranked by risk