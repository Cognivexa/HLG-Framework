---
name: web-artifacts-builder
description: Supplies a set of patterns for building self-contained web artifacts, such as dashboards, small tools, and multi-component apps, that run entirely from a single HTML file with no build step or external dependencies.
argument-hint: [app-idea]
---

# Web Artifacts Builder

Ships a working single-file app instead of a half-finished project scaffold.

## Input

$ARGUMENTS

## How It Works

1. Clarify the artifact type needed, whether a dashboard, form, game, or utility tool.
2. Select layout and interaction patterns proven to work well inside a single HTML document.
3. Inline all CSS and JavaScript directly in the file, avoiding any external build tooling.
4. Wire up state and interactivity using plain JavaScript or lightweight in-browser patterns only.
5. Test the artifact by opening it directly to confirm it renders and functions with zero setup steps.