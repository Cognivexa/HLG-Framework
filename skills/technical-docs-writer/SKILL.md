---
name: technical-docs-writer
description: Produce API references, how-to guides, and conceptual docs that follow a consistent structure and stay honest about edge cases.
argument-hint: [file-or-pattern]
---

# Technical Docs Writer

Write documentation that a new engineer can follow without pinging the author.

## Input

$ARGUMENTS

## How It Works

1. Read the code or spec being documented in full before writing
2. Choose the right doc type: reference, how-to, or conceptual
3. Write the happy path first, then call out edge cases explicitly
4. Include a runnable example wherever a signature is documented
5. Flag anything undocumented in the source that the reader would need