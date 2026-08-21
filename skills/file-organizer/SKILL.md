---
name: file-organizer
description: Organizes files and folders by reading their actual content rather than trusting filenames or extensions alone. It flags duplicate and near-duplicate files and proposes a cleaner folder structure grouped by topic and purpose.
argument-hint: [folder-path]
---

# File Organizer

Sorts by what a file actually contains instead of what it happens to be named.

## Input

$ARGUMENTS

## How It Works

1. Scan the target folder recursively and sample the content of each file, not just its name.
2. Cluster files by topic, project, and document type using content similarity.
3. Identify exact and near-duplicate files by comparing content hashes and text overlap.
4. Propose a revised folder hierarchy with clear category names and flag files that do not fit anywhere.
5. Apply the reorganization only after the user confirms the proposed structure and duplicate list.