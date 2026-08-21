---
name: mobile-bundle-size-audit
description: Analyzes an APK/AAB or IPA build artifact to break down size by module, asset type, and third-party library, then diffs against the previous release to flag regressions. Suggests concrete trims such as duplicate asset removal, unused resource stripping, and lazy-loadable modules.
argument-hint: [build-artifact-path]
---

# Mobile Bundle Size Auditor

Finds exactly what's bloating your app and how much each fix would save.

## Input

$ARGUMENTS

## How It Works

1. Unpack the APK/AAB or IPA build artifact
2. Measure size contribution per module, asset folder, and dependency
3. Compare against the previous build's stored size snapshot
4. Flag size regressions above a configurable threshold
5. Recommend concrete trims: duplicate assets, unused resources, lazy modules