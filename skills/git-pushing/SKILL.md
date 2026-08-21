---
name: git-pushing
description: Stages, commits, and pushes changes using well-formed conventional commit messages. It checks first for unrelated uncommitted work in the tree so it does not get swept into the same commit by accident.
argument-hint: [commit-message]
---

# Git Pushing

Commits what belongs together and leaves everything else exactly where it was.

## Input

$ARGUMENTS

## How It Works

1. Run a status check to separate changes relevant to the current task from unrelated modifications.
2. Stage only the files tied to the current change, never a blanket add of the whole tree.
3. Draft a conventional commit message with the correct type, scope, and a why-focused summary.
4. Create the commit and confirm it was recorded before attempting to push.
5. Push to the tracked remote branch and report the resulting commit hash and branch status.