---
name: app-store-release-notes
description: Turns a range of git commits or a sprint's ticket list into polished, user-facing release notes formatted for App Store Connect and Google Play listings. Produces both a full changelog and a trimmed "what's new" version that respects each store's character limits.
argument-hint: [version-tag-or-commit-range]
---

# App Store Release Notes Drafter

Turns raw commit noise into store-ready release notes in one pass.

## Input

$ARGUMENTS

## How It Works

1. Collect commits or PR titles across the specified range
2. Classify each change as feature, fix, improvement, or internal-only
3. Filter out internal changes that end users don't need to see
4. Rewrite technical descriptions into plain, user-facing language
5. Format two outputs: a full changelog and a character-limited "what's new" blurb