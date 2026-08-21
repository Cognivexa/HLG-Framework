---
name: create-slash-commands
description: Provides expert guidance for authoring Claude Code slash commands, covering front-matter fields, argument-hint conventions, ARGUMENTS usage, and keeping each command focused on a single job.
argument-hint: [command-name]
---

# Create Slash Commands

Turns a recurring prompt copy-pasted from chat history into a proper reusable command instead of another paragraph retyped every time.

## Input

$ARGUMENTS

## How It Works

1. Clarify the single job the command should perform and reject scope creep beyond that job.
2. Draft the front-matter, including a clear description and an argument-hint that matches expected input.
3. Write the command body so it substitutes ARGUMENTS cleanly and handles the no-argument case gracefully.
4. Decide whether the command should run inline or delegate to a subagent, based on its expected output length.
5. Test the command with representative arguments and tighten the wording until behavior is predictable.