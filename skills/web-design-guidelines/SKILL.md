---
name: web-design-guidelines
description: Audits a web interface or design mockup against a curated set of modern UI heuristics covering spacing, typography, contrast, hierarchy, and responsive behavior, then reports concrete fixes.
argument-hint: [file-or-folder]
---

# Web Design Guidelines

Turns a subjective is this UI good conversation into a checklist audit with line-level fixes instead of vague taste-based feedback.

## Input

$ARGUMENTS

## How It Works

1. Scan the provided markup, styles, or screenshot for spacing, alignment, and grid consistency issues.
2. Check text contrast ratios and font sizing against accessibility and legibility thresholds.
3. Evaluate visual hierarchy by checking whether heading weights, color, and whitespace correctly guide the eye.
4. Test layout behavior at common breakpoints and flag elements that break, overflow, or become unreadable.
5. Compile violations into a prioritized list, each paired with a specific CSS or markup change that resolves it.