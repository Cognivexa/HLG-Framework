---
name: create-claude-commands
description: Guides the authoring of a project's CLAUDE.md configuration file, covering what belongs in it, how to keep it concise, and how to phrase instructions so they are not ignored.
argument-hint: [project-path]
---

# Create Claude Commands

Turns a bloated CLAUDE.md nobody follows into a short file the model actually reads and obeys, instead of one it skims past.

## Input

$ARGUMENTS

## How It Works

1. Review the existing CLAUDE.md, if any, and separate load-bearing instructions from stale or generic filler.
2. Identify project conventions, such as build commands and file layout, that a model could not infer on its own.
3. Rewrite each instruction as a direct, specific statement rather than a vague preference.
4. Trim sections that duplicate what is already discoverable from the codebase itself.
5. Verify the final file stays short enough to be read in full each session while covering every must-follow rule.