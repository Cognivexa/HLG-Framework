---
name: commit-message-linter
description: Reviews a range of commits against Conventional Commits and imperative-mood style rules, flagging vague messages like "fix stuff" and suggesting rewrites grounded in the actual diff content. Also checks subject-line length and body wrapping conventions.
argument-hint: [commit-range]
---

# Commit Message Quality Checker

Catches lazy commit messages before they land in permanent history.

## Input

$ARGUMENTS

## How It Works

1. Read each commit's diff alongside its message
2. Check the subject line against Conventional Commits type/scope format
3. Flag vague or generic messages that don't match the diff content
4. Verify line length, imperative mood, and body wrapping conventions
5. Suggest a rewritten message grounded in what the diff actually changed