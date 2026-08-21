---
name: using-git-worktrees
description: Sets up a git worktree-based workspace when starting feature work that needs isolation from the main checkout. It keeps parallel branches of work from colliding over the same working directory.
argument-hint: [branch-name]
---

# Using Git Worktrees

Gives each branch its own working directory instead of one tree juggling every branch in turn.

## Input

$ARGUMENTS

## How It Works

1. Confirm the target branch and whether it already exists locally or needs to be created.
2. Create a new worktree in a dedicated directory tied to that branch.
3. Copy over any untracked local configuration the new worktree needs to run, such as environment files.
4. Point subsequent commands at the new worktree path so work stays isolated from the main checkout.
5. Remove the worktree cleanly once the branch is merged or abandoned to avoid stale directories.