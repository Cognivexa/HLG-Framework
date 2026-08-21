---
name: prompt-chain-builder
description: Design multi-step prompt chains with explicit inputs/outputs per step, so failures are traceable to one stage.
argument-hint: [task-description]
---

# Prompt Chain Builder

Break a fuzzy multi-step task into named stages with clear inputs and outputs.

## Input

$ARGUMENTS

## How It Works

1. Decompose the task into stages with a single clear responsibility each
2. Define the exact input and output shape for every stage
3. Add a validation check between stages to catch drift early
4. Recommend where a stage should be a schema-constrained call
5. Document the chain so failures can be traced to one stage