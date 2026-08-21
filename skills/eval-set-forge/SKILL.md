---
name: eval-set-forge
description: Builds structured evaluation datasets from raw production transcripts by clustering similar queries, sampling edge cases, and drafting rubric-based grading criteria.
argument-hint: [logs-path]
---

# Eval Set Forge

Turns a pile of production transcripts into a defensible, reusable eval suite in minutes.

## Input

$ARGUMENTS

## How It Works

1. Ingest raw transcripts and normalize them into a common schema.
2. Cluster queries by semantic similarity to surface distinct task types.
3. Stratified-sample across clusters and deliberately oversample outliers.
4. Draft a per-cluster grading rubric with explicit pass and fail criteria.
5. Export the eval set and rubrics as a versioned JSONL bundle.