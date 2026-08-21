---
name: style-guide-enforcer
description: Check prose against a project or brand style guide: terminology, tone, formatting, and voice consistency.
argument-hint: [file-or-pattern]
---

# Style Guide Enforcer

Enforce the style guide that already exists instead of relying on memory during review.

## Input

$ARGUMENTS

## How It Works

1. Load the project or brand style guide as the source of truth
2. Flag terminology that deviates from the approved glossary
3. Check tone and voice consistency across sections
4. Verify formatting conventions: headings, lists, code blocks
5. Return a diff-style report rather than silently rewriting