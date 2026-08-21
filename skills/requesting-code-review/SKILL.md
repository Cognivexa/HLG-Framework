---
name: requesting-code-review
description: Packages a finished change into a reviewable request by summarizing what changed, why, and which parts deserve the closest scrutiny, rather than submitting a bare diff link.
argument-hint: [pr-or-diff]
---

# Requesting Code Review

Turns a raw diff into a guided review request instead of leaving reviewers to reconstruct context themselves.

## Input

$ARGUMENTS

## How It Works

1. Summarize the intent of the change and the problem it solves in a short opening statement.
2. List the files touched and group them by logical purpose.
3. Call out any risky, complex, or non-obvious sections that warrant closer reading.
4. Note what testing was performed and what remains unverified.
5. Compile the summary, risk callouts, and testing notes into the review request before submission.