---
name: mcp-builder
description: Guides the design of a Model Context Protocol server by scoping each tool tightly, writing precise descriptions and schemas, and structuring error handling so agents can call it reliably.
argument-hint: [server-name]
---

# MCP Builder

Turns a grab-bag of API wrappers into a small set of well-scoped tools an agent can actually reason about, instead of one that gets ignored or misused.

## Input

$ARGUMENTS

## How It Works

1. Clarify the underlying system's capabilities and identify the smallest set of operations worth exposing as tools.
2. Draft a name and one-sentence description for each tool that states exactly when an agent should call it.
3. Define input and output schemas with explicit types, required fields, and realistic examples.
4. Design error responses that tell the calling agent what went wrong and what to try next, rather than raw stack traces.
5. Structure the server code so tools stay independent, testable, and easy to add to without touching existing ones.