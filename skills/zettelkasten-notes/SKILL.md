---
name: zettelkasten-notes
description: Capture atomic notes and link them into a Zettelkasten-style knowledge graph instead of a flat, unsearchable notes dump.
argument-hint: [note-text-or-file]
---

# Zettelkasten Notes

Turn raw notes into atomic, linkable knowledge instead of a pile of unstructured text.

## Input

$ARGUMENTS

## How It Works

1. Split incoming notes into single, atomic ideas
2. Check for existing related notes before creating a new one
3. Link each note to at least one existing note by idea, not by topic
4. Tag notes with retrievable, specific tags
5. Surface orphan notes with no links for review