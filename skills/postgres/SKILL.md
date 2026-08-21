---
name: postgres
description: Provides recommendation-only guidance for working against a PostgreSQL database, covering query design, indexing strategy, and reading EXPLAIN output. It never runs destructive statements without explicit confirmation from the user.
argument-hint: [query-or-schema]
---

# Postgres

Advises on the query and the index instead of just running whatever statement is handed to it.

## Input

$ARGUMENTS

## How It Works

1. Inspect the relevant schema, existing indexes, and table sizes before suggesting any change.
2. Draft the query with attention to join order, filter selectivity, and expected row counts.
3. Run EXPLAIN ANALYZE where safe and interpret the plan for sequential scans, missing indexes, or bad estimates.
4. Recommend specific index or query rewrites with the expected impact stated plainly.
5. Hold off on any destructive statement, such as DELETE, DROP, or TRUNCATE, until the user explicitly confirms it.