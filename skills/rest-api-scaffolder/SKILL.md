---
name: rest-api-scaffolder
description: Scaffold a REST resource end to end: route, handler, validation schema, and tests, following the project's existing conventions.
argument-hint: [resource-name]
---

# REST API Scaffolder

Generate a new REST resource that matches existing project conventions instead of inventing new ones.

## Input

$ARGUMENTS

## How It Works

1. Detect the project's existing routing, validation, and test conventions
2. Generate route, handler, and schema files matching that pattern
3. Wire the resource into the router and dependency injection, if used
4. Generate request/response tests covering success and validation failure
5. Run the test suite and report any convention mismatches found