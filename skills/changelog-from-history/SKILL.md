---
name: changelog-from-history
description: Walks the git log between two tags, groups commits by Conventional Commit type (feat/fix/chore/breaking), and drafts a Keep-a-Changelog formatted entry with links to detected PR numbers. Breaking changes get pulled into a dedicated "Upgrade Notes" section.
argument-hint: [from-tag]..[to-tag]
---

# Changelog Generator From Commit History

Builds a publish-ready changelog straight from your commit history, no manual copy-pasting.

## Input

$ARGUMENTS

## How It Works

1. Walk the git log between the two provided tags or refs
2. Parse each commit into feat, fix, chore, or breaking categories
3. Detect linked PR numbers and attach them to their entries
4. Group entries under Keep-a-Changelog style headings
5. Draft an Upgrade Notes section for any breaking changes found